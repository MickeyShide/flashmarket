"""Domain-level exceptions for the wishlist bounded context."""


class WishlistError(Exception):
    """Base exception for all wishlist domain errors."""

    code = "wishlist_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class ItemAlreadyInWishlist(WishlistError):
    """Raised when a product is already present in user's wishlist."""

    code = "item_already_in_wishlist"
    message = "Product is already in wishlist"


class ItemNotInWishlist(WishlistError):
    """Raised when trying to delete or access a product not in wishlist."""

    code = "item_not_in_wishlist"
    message = "Product is not in wishlist"


class WishlistLimitReached(WishlistError):
    """Raised when user exceeds maximum allowed items in wishlist."""

    code = "wishlist_limit_reached"
    message = "Wishlist item limit reached"
