#!/usr/bin/env python3
"""
Schedule JSON Creator - Guided tool for creating validated schedule JSON files.

This script interactively guides users through creating a schedule configuration
with input validation and formatted JSON output.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class ScheduleValidator:
    """Validates schedule configuration inputs."""
    
    # Valid values for known fields
    VALID_EXCHANGES = ["coinbase", "kraken", "test"]
    VALID_SCHEDULES = ["1H", "4H", "1D", "1W", "1M"]
    VALID_ALGORITHMS = ["oracle", "arbitrage"]
    
    @staticmethod
    def validate_asset(value: str) -> str:
        """Validate asset symbol (e.g., BTC, ETH)."""
        if not value:
            raise ValueError("Asset cannot be empty")
        asset = value.upper().strip()
        if not asset.isalpha():
            raise ValueError("Asset must contain only letters")
        if len(asset) > 10:
            raise ValueError("Asset symbol too long (max 10 characters)")
        return asset
    
    @staticmethod
    def validate_quote(value: str) -> str:
        """Validate quote currency (e.g., EUR, USD)."""
        if not value:
            raise ValueError("Quote currency cannot be empty")
        quote = value.upper().strip()
        if not quote.isalpha():
            raise ValueError("Quote must contain only letters")
        if len(quote) != 3:
            raise ValueError("Quote currency should be 3 letters (e.g., EUR, USD)")
        return quote
    
    @staticmethod
    def validate_schedule(value: str) -> str:
        """Validate schedule interval."""
        schedule = value.upper().strip()
        if schedule not in ScheduleValidator.VALID_SCHEDULES:
            valid = ", ".join(ScheduleValidator.VALID_SCHEDULES)
            raise ValueError(f"Schedule must be one of: {valid}")
        return schedule
    
    @staticmethod
    def validate_exchange(value: str) -> str:
        """Validate exchange name."""
        exchange = value.lower().strip()
        if exchange not in ScheduleValidator.VALID_EXCHANGES:
            valid = ", ".join(ScheduleValidator.VALID_EXCHANGES)
            raise ValueError(f"Exchange must be one of: {valid}")
        return exchange
    
    @staticmethod
    def validate_boolean(value: str) -> str:
        """Validate and normalize boolean value."""
        val_lower = value.lower().strip()
        if val_lower not in ["true", "false"]:
            raise ValueError("Must be 'true' or 'false'")
        return val_lower == "true"

    @staticmethod
    def validate_algorithm_type(value: str) -> str:
        """Validate algorithm type."""
        algorithm_type = value.lower().strip()
        if algorithm_type not in ScheduleValidator.VALID_ALGORITHMS:
            valid = ", ".join(ScheduleValidator.VALID_ALGORITHMS)
            raise ValueError(f"Algorithm type must be one of: {valid}")
        return algorithm_type

    @staticmethod
    def validate_float(value: str) -> float:
        """Validate a floating-point number."""
        try:
            return float(value.strip())
        except ValueError as exc:
            raise ValueError("Must be a number") from exc

    @staticmethod
    def validate_non_negative_float(value: str) -> float:
        """Validate a non-negative floating-point number."""
        number = ScheduleValidator.validate_float(value)
        if number < 0:
            raise ValueError("Must be 0 or greater")
        return number


class ScheduleCreator:
    """Interactive schedule creator with validation."""
    
    def __init__(self):
        self.schedule_data: Dict[str, Any] = {}
        self.validator = ScheduleValidator()

    def get_optional_input(self, prompt: str, default: Optional[str] = None) -> Optional[str]:
        """Get optional user input."""
        if default is not None:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input or default
        return input(f"{prompt}: ").strip() or None
    
    def get_validated_input(self, prompt: str, validator_func, 
                          default: Optional[str] = None) -> Any:
        """Get user input with validation and retry logic."""
        while True:
            try:
                if default:
                    user_input = input(f"{prompt} [{default}]: ").strip()
                    if not user_input:
                        user_input = default
                else:
                    user_input = input(f"{prompt}: ").strip()
                
                if not user_input:
                    print("Input cannot be empty")
                    continue
                
                return validator_func(user_input)
            except ValueError as e:
                print(f"❌ Invalid input: {e}")
                print("Please try again.\n")

    def build_algorithm(self, asset: str, quote: str) -> Dict[str, Any]:
        """Collect strategy-specific algorithm settings."""
        print("Valid strategy types: oracle, arbitrage")
        algo_type = self.get_validated_input(
            "Enter strategy type",
            self.validator.validate_algorithm_type,
            default="oracle"
        )
        print(f"✓ Strategy type: {algo_type}\n")

        algorithm_name = self.get_optional_input(
            "Enter algorithm name",
            default=f"{asset.lower()}-{quote.lower()}-{algo_type}"
        )
        description = self.get_optional_input(
            "Enter algorithm description",
            default=f"{algo_type.title()} strategy for {asset}/{quote}"
        )

        buy_threshold = self.get_validated_input(
            "Enter buy threshold percentage",
            self.validator.validate_float,
            default="-1.0"
        )
        sell_threshold = self.get_validated_input(
            "Enter sell threshold percentage",
            self.validator.validate_float,
            default="1.0"
        )
        sell_below_cost_basis = self.get_validated_input(
            "Allow selling below cost basis? (true/false)",
            self.validator.validate_boolean,
            default="false"
        )

        algorithm = {
            "name": algorithm_name,
            "description": description,
            "algo_type": algo_type,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "sell_below_cost_basis": sell_below_cost_basis,
            "buy_percentage": 0.0,
            "sell_percentage": 0.0,
            "min_buy_value": 0.0,
            "min_sell_value": 0.0,
            "fixed_buy_value": 0.0,
            "fixed_sell_value": 0.0,
            "minimum_profit_percentage": 0.0,
        }

        if algo_type == "oracle":
            algorithm["buy_percentage"] = self.get_validated_input(
                "Enter buy percentage as decimal (e.g., 0.10 = 10%)",
                self.validator.validate_non_negative_float,
                default="0.10"
            )
            algorithm["sell_percentage"] = self.get_validated_input(
                "Enter sell percentage as decimal (e.g., 0.10 = 10%)",
                self.validator.validate_non_negative_float,
                default="0.10"
            )
            algorithm["min_buy_value"] = self.get_validated_input(
                "Enter minimum buy value in quote currency",
                self.validator.validate_non_negative_float,
                default="10.0"
            )
            algorithm["min_sell_value"] = self.get_validated_input(
                "Enter minimum sell value in quote currency",
                self.validator.validate_non_negative_float,
                default="10.0"
            )
        else:
            algorithm["fixed_buy_value"] = self.get_validated_input(
                "Enter fixed buy value in quote currency",
                self.validator.validate_non_negative_float,
                default="100.0"
            )
            algorithm["fixed_sell_value"] = self.get_validated_input(
                "Enter fixed sell value in quote currency",
                self.validator.validate_non_negative_float,
                default="100.0"
            )
            algorithm["minimum_profit_percentage"] = self.get_validated_input(
                "Enter minimum profit percentage",
                self.validator.validate_non_negative_float,
                default="0.0"
            )

        print(f"✓ Algorithm configured: {algorithm_name}\n")
        return algorithm

    def build_portfolio(self, asset: str, quote: str, exchange: str) -> Dict[str, Any]:
        """Collect portfolio values required by strategy execution."""
        print("Portfolio values are used when creating buy/sell orders.")
        initial_asset_amount = self.get_validated_input(
            "Enter initial asset amount",
            self.validator.validate_non_negative_float,
            default="0.0"
        )
        initial_cost_basis = self.get_validated_input(
            "Enter initial cost basis",
            self.validator.validate_non_negative_float,
            default="0.0"
        )
        current_quote_amount = self.get_validated_input(
            "Enter current quote amount",
            self.validator.validate_non_negative_float,
            default="0.0"
        )
        
        portfolio = {
            "asset": asset,
            "quote": quote,
            "exchange": exchange,
            "initial_asset_amount": initial_asset_amount,
            "initial_cost_basis": initial_cost_basis,
            "trades": [],
            "current_cost_basis": initial_cost_basis,
            "current_asset_amount": initial_asset_amount,
            "current_quote_amount": current_quote_amount,
            "current_net_worth": 0.0,
            "last_updated": self.get_optional_input(
                "Enter portfolio last updated timestamp or press Enter for null",
                default="null"
            ),
        }
        print("✓ Portfolio configured\n")
        return portfolio
    
    def create_schedule(self) -> Dict[str, Any]:
        """Interactively create a schedule configuration."""
        print("\n" + "="*60)
        print("  SCHEDULE JSON CREATOR")
        print("="*60 + "\n")
        
        # Asset
        asset = self.get_validated_input(
            "Enter asset symbol (e.g., BTC, ETH)",
            self.validator.validate_asset
        )
        self.schedule_data["asset"] = asset
        print(f"✓ Asset: {asset}\n")
        
        # Quote currency
        quote = self.get_validated_input(
            "Enter quote currency (e.g., EUR, USD)",
            self.validator.validate_quote
        )
        self.schedule_data["quote"] = quote
        print(f"✓ Quote: {quote}\n")
        
        # Schedule interval
        print("Valid schedules: 1H, 4H, 1D, 1W, 1M")
        schedule = self.get_validated_input(
            "Enter schedule interval",
            self.validator.validate_schedule
        )
        self.schedule_data["schedule"] = schedule
        print(f"✓ Schedule: {schedule}\n")
        
        # Last execution
        last_execution = input("Enter last execution time or press Enter for 'null': ").strip()
        if not last_execution or last_execution.lower() == "null":
            self.schedule_data["last_execution"] = "null"
        else:
            self.schedule_data["last_execution"] = last_execution
        print(f"✓ Last execution: {self.schedule_data['last_execution']}\n")
        
        # Exchange
        print(f"Valid exchanges: {', '.join(self.validator.VALID_EXCHANGES)}")
        exchange = self.get_validated_input(
            "Enter exchange",
            self.validator.validate_exchange,
            default="coinbase"
        )
        self.schedule_data["exchange"] = exchange
        print(f"✓ Exchange: {exchange}\n")
        
        # Active status
        active = self.get_validated_input(
            "Is this schedule active? (true/false)",
            self.validator.validate_boolean,
            default="true"
        )
        self.schedule_data["active"] = active
        print(f"✓ Active: {active}\n")
        
        # Buy and sell
        buy_sell = self.get_validated_input(
            "Enable buy and sell? (true/false)",
            self.validator.validate_boolean,
            default="false"
        )
        self.schedule_data["buy_and_sell"] = buy_sell
        print(f"✓ Buy and sell: {buy_sell}\n")

        self.schedule_data["algorithm"] = self.build_algorithm(asset, quote)
        self.schedule_data["portfolio"] = self.build_portfolio(asset, quote, exchange)
        
        return self.schedule_data
    
    def format_json(self, indent: int = 4) -> str:
        """Format the schedule data as a JSON string."""
        return json.dumps(self.schedule_data, indent=indent)
    
    def display_result(self):
        """Display the formatted JSON result."""
        print("="*60)
        print("  SCHEDULE JSON OUTPUT")
        print("="*60)
        print(self.format_json())
        print("="*60 + "\n")
    
    def save_to_file(self, filepath: Optional[str] = None) -> Optional[str]:
        """Save the schedule to a JSON file."""
        if filepath is None:
            filepath = input("Enter filename to save (or press Enter to skip): ").strip()
        
        if not filepath:
            return None
        
        # Add .json extension if not provided
        if not filepath.endswith(".json"):
            filepath += ".json"
        
        # Ensure parent directory exists
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, "w") as f:
                f.write(self.format_json())
            print(f"✓ Schedule saved to: {filepath}\n")
            return filepath
        except IOError as e:
            print(f"❌ Error saving file: {e}\n")
            return None


def main():
    """Main entry point."""
    try:
        creator = ScheduleCreator()
        creator.create_schedule()
        creator.display_result()
        
        # Ask if user wants to save
        save_choice = input("Do you want to save this to a file? (y/n): ").strip().lower()
        if save_choice in ["y", "yes"]:
            creator.save_to_file()
        
        print("✓ Schedule creation complete!")
        
    except KeyboardInterrupt:
        print("\n\n✓ Schedule creation cancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
