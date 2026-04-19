from azure.cosmos import CosmosClient, DatabaseProxy, ContainerProxy

import os
import datetime
from typing import List

from schedule import Schedule
from price import Price


URL = os.environ['ACCOUNT_URI']
KEY = os.environ['ACCOUNT_KEY']
DATABASE_NAME = os.environ['DATABASE_NAME']
SCHEDULE_CONTAINER = "schedule"
PRICES_CONTAINER = "price"

_client: CosmosClient = None
_database_client: DatabaseProxy = None
_schedule_client: ContainerProxy = None
_price_client: ContainerProxy = None


def client() -> CosmosClient:
    global _client
    if _client is None:
        _client = CosmosClient(URL, credential=KEY)
    return _client


def database_client() -> CosmosClient:
    global _database_client
    if _database_client is None:
        _database_client = client().get_database_client(DATABASE_NAME)
    return _database_client

def schedule_client() -> CosmosClient:
    global _schedule_client
    if _schedule_client is None:
        _schedule_client = database_client().get_container_client(SCHEDULE_CONTAINER)
    return _schedule_client

def price_client() -> CosmosClient:
    global _price_client
    if _price_client is None:
        _price_client = database_client().get_container_client(PRICES_CONTAINER)
    return _price_client


def get_active_schedules() -> List[Schedule]:
    return [Schedule(**item) for item in schedule_client().query_items(
        query="SELECT * FROM c WHERE c.active = true",
        enable_cross_partition_query=True)]


def upsert_schedule(schedule: Schedule) -> None:
    schedule_client().upsert_item(schedule.__dict__)


def persist_price(price: Price) -> None:
    price_client().insert_item(price.__dict__)


def get_prices(asset: str, quote: str, schedule: str, exchange: str, max_items: int = None) -> List[Price]:
    if max_items is None:
        query="SELECT * FROM c WHERE c.asset = @asset AND c.quote = @quote AND c.active = true AND c.schedule = @schedule AND c.exchange = @exchange ORDER BY c.timestamp DESC"
    else: 
        query=f"SELECT TOP {max_items} * FROM c WHERE c.asset = @asset AND c.quote = @quote AND c.active = true AND c.schedule = @schedule AND c.exchange = @exchange ORDER BY c.timestamp DESC"
    return [Price(**price) for price in price_client().query_items(
        query=query,
        parameters=[
            {"name": "@asset", "value": asset},
            {"name": "@quote", "value": quote},
            {"name": "@schedule", "value": schedule},
            {"name": "@exchange", "value": exchange}
        ],
        enable_cross_partition_query=True)]
