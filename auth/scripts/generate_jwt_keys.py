import argparse
from pathlib import Path

from auth_service.config import get_settings
from auth_service.key_management import generate_jwt_key_pair


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an Ed25519 key pair for FlashMarket access tokens"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("keys"),
        help="Key ring directory containing private/ and public/ subdirectories",
    )
    parser.add_argument(
        "--key-id",
        default=get_settings().jwt_key_id,
        help="Identifier used in the JWT kid header and key filenames",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing key pair and invalidate issued access tokens",
    )
    args = parser.parse_args()

    private_path, public_path = generate_jwt_key_pair(
        args.output_dir,
        key_id=args.key_id,
        force=args.force,
    )
    print(f"JWT private key: {private_path}")
    print(f"JWT public key:  {public_path}")


if __name__ == "__main__":
    main()
