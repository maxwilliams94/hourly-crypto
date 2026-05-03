import logging

from order import Order
from schedule import Schedule
from algorithm import Algorithm
from portfolio import Portfolio


def create_order(schedule: Schedule, current_price: float, previous_price: float):
    if previous_price is None or current_price is None:
        logging.warning(f"Missing price data for schedule {schedule.id}. Current price: {current_price}, Previous price: {previous_price}")
        return None

    absolute_price_change = current_price - previous_price
    percentage_price_change = (absolute_price_change / previous_price) * 100 if previous_price != 0 else 0.0
    if schedule.algorithm.algo_type == "oracle":
        if schedule.portfolio is None:
            logging.warning(f"Schedule {schedule.id} has no portfolio assigned. Cannot create order for oracle algorithm.")
            return None
        if percentage_price_change > schedule.algorithm.buy_threshold:
            logging.debug("Buy signal detected based on percentage price change: {:.2f}% > {:.2f}%".format(percentage_price_change, schedule.algorithm.buy_threshold))
            base_amount = (schedule.algorithm.buy_percentage * schedule.portfolio.current_quote_amount) / current_price
            base_amount = max(base_amount, schedule.algorithm.min_buy_value / current_price)
            # Buy signal
            order = Order(
                asset=schedule.asset,
                quote=schedule.quote,
                exchange=schedule.exchange,
                base_amount=base_amount,
                quote_amount=base_amount * current_price,
                price=current_price,
                direction="buy",
                order_type="limit",
                execution_active=schedule.buy_and_sell,
                status="pending"
            )
            return order
        elif percentage_price_change < schedule.algorithm.sell_threshold:
            logging.debug("Sell signal detected based on percentage price change: {:.2f}% < {:.2f}%".format(percentage_price_change, schedule.algorithm.sell_threshold))
            if (not schedule.algorithm.sell_below_cost_basis and current_price < schedule.portfolio.current_cost_basis):
                logging.debug("Sell signal ignored because current price is below cost basis and sell_below_cost_basis is False. Current price: {:.2f}, Cost basis: {:.2f}".format(current_price, schedule.portfolio.current_cost_basis))
                return None
            base_amount = (schedule.algorithm.sell_percentage * schedule.portfolio.current_asset_amount)
            base_amount = max(base_amount, schedule.algorithm.min_sell_value / current_price)
            # Sell signal
            order = Order(
                asset=schedule.asset,
                quote=schedule.quote,
                base_amount=base_amount,
                exchange=schedule.exchange,
                quote_amount=base_amount * current_price,
                price=current_price,
                direction="sell",
                order_type="limit",
                execution_active=schedule.buy_and_sell,
                status="pending"
            )
            return order

    elif schedule.algorithm.algo_type == "arbitrage":
        if percentage_price_change > schedule.algorithm.buy_threshold:
            logging.debug("Buy signal detected based on absolute price change: {:.2f} < {:.2f}".format(current_price, schedule.algorithm.buy_threshold))
            base_amount = (schedule.algorithm.fixed_buy_value / current_price)
            # Buy signal
            order = Order(
                asset=schedule.asset,
                quote=schedule.quote,
                exchange=schedule.exchange,
                base_amount=base_amount,
                quote_amount=schedule.algorithm.fixed_buy_value,
                price=current_price,
                direction="buy",
                order_type="limit",
                execution_active=schedule.buy_and_sell,
                status="pending"
            )
            return order
        elif percentage_price_change < schedule.algorithm.sell_threshold:
            logging.debug("Sell signal detected based on absolute price change: {:.2f} > {:.2f}".format(current_price, schedule.algorithm.sell_threshold))
            if (not schedule.algorithm.sell_below_cost_basis and current_price < schedule.portfolio.current_cost_basis):
                logging.debug("Sell signal ignored because current price is below cost basis and sell_below_cost_basis is False. Current price: {:.2f}, Cost basis: {:.2f}".format(current_price, schedule.portfolio.current_cost_basis))
                return None
            base_amount = (schedule.algorithm.fixed_sell_value / current_price)
            # Sell signal
            order = Order(
                asset=schedule.asset,
                quote=schedule.quote,
                exchange=schedule.exchange,
                base_amount=base_amount,
                quote_amount=schedule.algorithm.fixed_sell_value,
                price=current_price,
                direction="sell",
                order_type="limit",
                execution_active=schedule.buy_and_sell,
                status="pending"
            )
            return order
