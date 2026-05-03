import datetime
import logging
import os
from typing import List

import azure.functions as func

from scheduling import get_schedules, is_ready_for_next_execution, Schedule, update_schedule, register_execution
from exchange import get_current_price, execute_order, check_exchange_connectivity, update_trade
from prices import get_previous_price, save_price
from order import Order
from portfolio import Trade, update_portfolio_trades, update_portfolio_value
from price import Price
from decision import create_order

# Configure logging
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)


# Create the function app instance
app = func.FunctionApp()

@app.timer_trigger(schedule="%TIMER_SCHEDULE%", 
                   arg_name="execution_timer", 
                   run_on_startup=True,
                   use_monitor=True) 
def timer_function(execution_timer: func.TimerRequest) -> None:
    """
    Timer-triggered function that executes on a schedule defined by TIMER_SCHEDULE app setting.
    
    Args:
        execution_timer: Timer information including schedule status
    
    Notes:
        The run_on_startup=True parameter is useful for development and testing as it triggers
        the function immediately when the host starts, but should typically be set to False
        in production to avoid unexpected executions during deployments or restarts.
    """
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logging.info(f'Python timer trigger function executed at: {utc_timestamp}')
    logger.debug(f'Timer trigger details - Schedule status: {execution_timer.schedule_status}, Past due: {execution_timer.past_due}')

    schedules: List[Schedule] = get_schedules()
    logger.debug(f'Retrieved {len(schedules)} schedules from configuration')
    now = datetime.datetime.now(datetime.timezone.utc)
    logger.debug(f'Current UTC time: {now.isoformat()}')
    checked_exchanges = {}
    for schedule in schedules:
        logger.debug(f'Processing schedule for {schedule.asset}/{schedule.quote} on {schedule.exchange}')
        if schedule.exchange not in checked_exchanges:
            logging.info(f"Checking exchange: {schedule.exchange}")
            if check_exchange_connectivity(schedule.exchange):
                logging.info(f"Successfully connected to exchange: {schedule.exchange}")
                checked_exchanges[schedule.exchange] = True
            else:
                logging.error(f"Failed to connect to exchange: {schedule.exchange}. Skipping schedules for this exchange.")
                checked_exchanges[schedule.exchange] = False
                continue
        else:
            if not checked_exchanges[schedule.exchange]:
                logging.error(f"Skipping schedule for exchange: {schedule.exchange} due to previous connectivity failure.")
                continue
    

        unfilled_trades = [trade for trade in schedule.portfolio.trades if not trade.is_complete()] if schedule.portfolio else []
        logger.debug(f'Found {len(unfilled_trades)} unfilled trades for this schedule')
        updated_trades = {}  # Map of old trade id to new trade object
        for unfilled_trade in unfilled_trades:
            changed, updated_trade = update_trade(unfilled_trade)
            logger.debug(f'Trade update - Changed: {changed}, Trade ID: {unfilled_trade.id}')
            if changed:
                logging.info(f"Updated trade: {updated_trade}")
                updated_trades[unfilled_trade.id] = updated_trade
        
        if updated_trades:
            # Update trades in the portfolio with their new versions
            schedule.portfolio.trades = [
                updated_trades.get(t.id, t) for t in schedule.portfolio.trades
            ]
            update_schedule(schedule)
            logger.debug(f'Schedule updated due to trade status changes')

        if schedule.portfolio and update_portfolio_trades(schedule.portfolio):
            logger.info(f"Portfolio updated for schedule: {schedule.id}")
            update_schedule(schedule)

        # Fetch current price early so we can update portfolio value
        logger.debug(f'Fetching current price for {schedule.asset}/{schedule.quote}')
        current_price: Price = get_current_price(schedule.asset, schedule.quote, schedule.exchange)
        
        # Update portfolio with current market value
        if schedule.portfolio and current_price is not None:
            update_portfolio_value(schedule.portfolio, current_price.price)
            logger.debug(f'Portfolio value updated with current price')
            update_schedule(schedule)

        is_ready = is_ready_for_next_execution(schedule, now)
        logger.debug(f'Schedule ready for execution: {is_ready}')
        if not is_ready:
            continue
        else:
            logger.info(f"Executing scheduled task for schedule: {schedule.id}")
            logger.debug(f'Fetching previous price for {schedule.asset}/{schedule.quote}')
            previous_price: Price = get_previous_price(schedule.asset, schedule.quote, schedule.schedule, schedule.exchange)
            if schedule.algorithm is not None:
                is_valid, _ = schedule.algorithm.validate()
                if not is_valid:
                    logging.error(f"Skipping order creation for schedule {schedule.id}: algorithm '{schedule.algorithm.name}' is misconfigured.")
                    if current_price is not None:
                        current_price.schedule = schedule.schedule
                        save_price(current_price)
                    continue
            order: Order = create_order(schedule, current_price.price, previous_price.price)
            logger.debug(f'Order creation result: {order}')
            if order is not None:
                logging.info(f"Generated order: {order}")
                trade: Trade = execute_order(order)
                if trade is not None:
                    logging.info(f"Executed trade: {trade}")
                    schedule.portfolio.trades.append(trade)
            else:
                logging.info(f"No order generated for schedule: {schedule}")
        if (current_price is not None):
            current_price.schedule = schedule.schedule
            logger.debug(f'Persisting price data: {current_price}')
            save_price(current_price)
    
        logging.debug(f'Updating last execution time for schedule: {schedule.id}')
        register_execution(schedule, now)
    logger.debug('Schedule processing loop completed')
    
    if execution_timer.past_due:
        logging.warning('The timer is running late!')