from dataclasses import dataclass




@dataclass
class VaultEntry:
    key_name: str
    private_key: str
    api_key: str


"""
Return auth details for a given exchange. If vault is not supported, look in environment variables
"""
def get_auth(exchange: str) -> VaultEntry:
    pass
