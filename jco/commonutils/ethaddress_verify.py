from eth_utils import is_address, is_checksum_address, is_normalized_address


def is_valid_address(address: str) -> bool:
    return is_address(address) and (is_checksum_address(address) or is_normalized_address(address))
