"""Shared Complex Tool Implementations for Agent Examples.

These tools are designed to demonstrate StreamBlocks' advantages:
- Complex schemas (nested objects, enums, arrays)
- Slow execution (simulated network latency)
- Realistic e-commerce scenario

The simulated latency is crucial for comparing:
- Speculative: Tools run in parallel with LLM streaming
- Batched: All tools run after LLM, results injected together
- Sequential: Tools run after LLM, one at a time
- Native (Pydantic AI): Blocked waiting for each tool
"""

from __future__ import annotations

import asyncio
import random
import re
import string
from datetime import date, datetime, timedelta
from enum import IntEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# ENUMS
# =============================================================================


class RamSize(IntEnum):
    """Valid RAM sizes in GB."""

    GB_8 = 8
    GB_16 = 16
    GB_32 = 32
    GB_48 = 48
    GB_64 = 64
    GB_128 = 128


# =============================================================================
# PYDANTIC MODELS (For Pydantic AI / Gemini compatibility)
# =============================================================================


class PriceRange(BaseModel):
    """Price range filter with min and max values."""

    min: float = 0.0  # Default to 0 if not provided
    max: float


class Filter(BaseModel):
    """Filter object for product search."""

    field: Literal["specs.ram_gb", "specs.storage_gb", "rating"] = Field(
        description="Field to filter on: specs.ram_gb for RAM, specs.storage_gb for storage, rating for product rating."
    )
    operator: Literal[">=", "<=", "==", "!="] = Field(description="Comparison operator.")
    value: int = Field(
        description="Numeric value to compare. For RAM: 8, 16, 32, 64, 128. For storage: 256, 512, 1024, 2048. For rating: 1-5."
    )


class ShippingAddress(BaseModel):
    """Shipping address for orders."""

    street: str
    city: str
    state: str
    zip: str
    country: str

    @field_validator("zip", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:
        """Coerce zip to string (YAML may parse as int)."""
        return str(v)


class OrderItem(BaseModel):
    """Order item with product and quantity."""

    product_id: str
    quantity: int


class DateRange(BaseModel):
    """Date range for analytics queries."""

    start: str
    end: str

    @field_validator("start", "end", mode="before")
    @classmethod
    def normalize_date(cls, v: str | date) -> str:
        """Convert datetime.date to ISO string if needed.

        YAML automatically parses ISO date strings (e.g., 2023-10-01) into
        datetime.date objects. This validator normalizes them back to strings.
        """
        if isinstance(v, date):
            return v.isoformat()
        return v


# =============================================================================
# PRODUCT DATA (Mock database)
# =============================================================================

# Valid product IDs for validation
VALID_PRODUCT_IDS = {"laptop-001", "laptop-002", "laptop-003", "laptop-004"}

PRODUCTS = [
    {
        "id": "laptop-001",
        "name": "ProBook Developer 16",
        "category": "electronics",
        "price": 1299.99,
        "specs": {"ram_gb": 16, "storage_gb": 512, "cpu": "Intel i7-12700H"},
        "rating": 4.7,
        "in_stock": True,
    },
    {
        "id": "laptop-002",
        "name": "CodeMaster Pro X",
        "category": "electronics",
        "price": 1449.99,
        "specs": {"ram_gb": 32, "storage_gb": 1024, "cpu": "AMD Ryzen 9 7940HS"},
        "rating": 4.9,
        "in_stock": True,
    },
    {
        "id": "laptop-003",
        "name": "DevStation Ultra",
        "category": "electronics",
        "price": 1199.99,
        "specs": {"ram_gb": 16, "storage_gb": 512, "cpu": "Intel i5-12500H"},
        "rating": 4.5,
        "in_stock": True,
    },
    {
        "id": "laptop-004",
        "name": "ThinkDev Enterprise",
        "category": "electronics",
        "price": 1599.99,
        "specs": {"ram_gb": 64, "storage_gb": 2048, "cpu": "Intel i9-13900H"},
        "rating": 4.8,
        "in_stock": False,
    },
]


# =============================================================================
# COMPLEX TOOL IMPLEMENTATIONS
# =============================================================================


async def search_products_impl(
    query: str,
    category: Literal["electronics", "clothing", "home", "sports"],
    price_range: PriceRange,
    filters: list[Filter],
    sort_by: str = "relevance",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search product catalog with complex filters.

    Args:
        query: Search query string (e.g., "laptop", "programming laptop")
        category: Product category to search in
        price_range: Price range filter with "min" and "max" keys
        filters: List of filter objects, each with "field", "operator", "value"
                 Example: [{"field": "specs.ram_gb", "operator": ">=", "value": 16}]
        sort_by: Sort order - "relevance", "price_asc", "price_desc", "rating"
        limit: Maximum number of results to return

    Returns:
        List of matching products with id, name, price, specs, rating
    """
    # Simulate API latency (database query + search index)
    await asyncio.sleep(1.2)

    # Filter products
    results = []
    for product in PRODUCTS:
        # Category filter
        if product["category"] != category:
            continue

        # Price range filter
        min_price = price_range.min
        max_price = price_range.max
        if not (min_price <= product["price"] <= max_price):
            continue

        # Apply custom filters
        matches_filters = True
        for f in filters:
            field = f.field
            operator = f.operator
            value = f.value

            # Handle nested fields (e.g., "specs.ram_gb")
            field_value = product
            for key in field.split("."):
                if isinstance(field_value, dict):
                    field_value = field_value.get(key)
                else:
                    field_value = None
                    break

            if field_value is None:
                matches_filters = False
                break

            # Apply operator
            if (
                (operator == ">=" and field_value < value)
                or (operator == "<=" and field_value > value)
                or (operator == "==" and field_value != value)
                or (operator == "!=" and field_value == value)
            ):
                matches_filters = False

        if not matches_filters:
            continue

        # Query matching (simple substring or generic terms)
        query_lower = query.lower()
        name_lower = product["name"].lower()
        generic_terms = ["laptop", "computer", "notebook", "dev", "programming"]

        # Check if query is in product name, or any word in query matches generic terms
        query_words = query_lower.split()
        matches_query = (
            query_lower in name_lower
            or any(term in name_lower for term in query_words)
            or any(term in generic_terms for term in query_words)
        )
        if not matches_query:
            continue

        results.append(product)

    # Sort results
    if sort_by == "price_asc":
        results.sort(key=lambda x: x["price"])
    elif sort_by == "price_desc":
        results.sort(key=lambda x: x["price"], reverse=True)
    elif sort_by == "rating":
        results.sort(key=lambda x: x["rating"], reverse=True)

    return results[:limit]


async def create_order_impl(
    customer_id: str,
    items: list[OrderItem],
    shipping_address: ShippingAddress,
    payment_method: Literal["credit_card", "paypal", "bank_transfer"],
    coupon_code: str | None = None,
) -> dict[str, Any]:
    """Create a new order with nested objects.

    IMPORTANT: You MUST call search_products FIRST and emit a wait block to get
    valid product IDs before calling this function. Do NOT guess or make up
    product IDs - use only the exact IDs returned by search_products.

    Example workflow:
    1. Emit a tool_call block for search_products
    2. Emit a wait block listing the search_products tool_call ID
    3. After receiving results, emit a tool_call block for create_order with real IDs

    Args:
        customer_id: The customer's unique identifier
        items: List of order items, each with:
               - product_id: Product ID from search_products results (REQUIRED)
               - quantity: Number of units
               - options: Optional customization (e.g., {"color": "silver"})
        shipping_address: Shipping address with:
                          - street: Street address
                          - city: City name
                          - state: State/province
                          - zip: ZIP/postal code
                          - country: Country code (e.g., "US")
        payment_method: Payment type - "credit_card", "paypal", or "bank_transfer"
        coupon_code: Optional discount coupon code

    Returns:
        Order confirmation with order_id, total, estimated_delivery, status
    """
    # Validate product IDs before processing
    for item in items:
        if item.product_id not in VALID_PRODUCT_IDS:
            return {
                "error": f"Invalid product_id: {item.product_id}. "
                f"Valid IDs are: {', '.join(sorted(VALID_PRODUCT_IDS))}. "
                "Use search_products first to find valid product IDs."
            }

    # Simulate database write and payment processing
    await asyncio.sleep(1.5)

    # Calculate total
    total = 0.0
    order_items = []

    for item in items:
        product_id = item.product_id
        quantity = item.quantity

        # Find product
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if product:
            item_total = product["price"] * quantity
            total += item_total
            order_items.append(
                {
                    "product_id": product_id,
                    "name": product["name"],
                    "quantity": quantity,
                    "unit_price": product["price"],
                    "total": item_total,
                }
            )

    # Apply coupon
    discount = 0.0
    if coupon_code:
        if coupon_code.upper() == "SAVE10":
            discount = total * 0.10
        elif coupon_code.upper() == "SAVE20":
            discount = total * 0.20

    final_total = total - discount

    # Generate order ID
    order_id = "ORD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Calculate estimated delivery
    delivery_date = datetime.now() + timedelta(days=random.randint(3, 7))

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "items": order_items,
        "subtotal": total,
        "discount": discount,
        "total": final_total,
        "shipping_address": shipping_address.model_dump(),
        "payment_method": payment_method,
        "status": "confirmed",
        "estimated_delivery": delivery_date.strftime("%Y-%m-%d"),
    }


async def get_analytics_impl(
    metric_type: Literal["sales", "traffic", "conversion"],
    date_range: DateRange,
    granularity: Literal["hour", "day", "week", "month"],
    dimensions: list[str],
) -> dict[str, Any]:
    """Get analytics data with aggregations.

    Args:
        metric_type: Type of metric - "sales", "traffic", or "conversion"
        date_range: Date range with "start" and "end" keys (ISO format: YYYY-MM-DD)
        granularity: Time granularity - "hour", "day", "week", or "month"
        dimensions: Dimensions to group by - any of:
                    - "product": Group by product
                    - "category": Group by category
                    - "region": Group by geographic region
                    - "channel": Group by sales channel

    Returns:
        Analytics data with time series, breakdown by dimensions, and summary stats
    """
    # Simulate analytics query (aggregation is slow)
    await asyncio.sleep(2.0)

    # Generate mock analytics data
    start_date = datetime.fromisoformat(date_range.start)
    end_date = datetime.fromisoformat(date_range.end)

    # Generate time series data
    time_series = []
    current = start_date
    while current <= end_date:
        if metric_type == "sales":
            value = random.uniform(5000, 15000)
        elif metric_type == "traffic":
            value = random.randint(1000, 5000)
        else:  # conversion
            value = random.uniform(0.02, 0.08)

        time_series.append({"date": current.strftime("%Y-%m-%d"), "value": round(value, 2)})

        if granularity == "hour":
            current += timedelta(hours=1)
        elif granularity == "day":
            current += timedelta(days=1)
        elif granularity == "week":
            current += timedelta(weeks=1)
        else:  # month
            current += timedelta(days=30)

    # Generate dimension breakdowns
    breakdowns = {}

    if "category" in dimensions:
        breakdowns["category"] = [
            {"name": "electronics", "value": random.uniform(40000, 80000)},
            {"name": "clothing", "value": random.uniform(20000, 40000)},
            {"name": "home", "value": random.uniform(15000, 30000)},
            {"name": "sports", "value": random.uniform(10000, 25000)},
        ]

    if "region" in dimensions:
        breakdowns["region"] = [
            {"name": "North America", "value": random.uniform(50000, 100000)},
            {"name": "Europe", "value": random.uniform(30000, 60000)},
            {"name": "Asia Pacific", "value": random.uniform(20000, 50000)},
        ]

    if "channel" in dimensions:
        breakdowns["channel"] = [
            {"name": "Direct", "value": random.uniform(40000, 70000)},
            {"name": "Organic Search", "value": random.uniform(20000, 40000)},
            {"name": "Paid Ads", "value": random.uniform(15000, 35000)},
            {"name": "Social Media", "value": random.uniform(10000, 25000)},
        ]

    # Calculate summary
    total_value = sum(point["value"] for point in time_series)
    avg_value = total_value / len(time_series) if time_series else 0

    return {
        "metric_type": metric_type,
        "date_range": date_range,
        "granularity": granularity,
        "time_series": time_series[:10],  # Limit for readability
        "breakdowns": breakdowns,
        "summary": {
            "total": round(total_value, 2),
            "average": round(avg_value, 2),
            "min": round(min(p["value"] for p in time_series), 2) if time_series else 0,
            "max": round(max(p["value"] for p in time_series), 2) if time_series else 0,
            "trend": random.choice(["up", "down", "stable"]),
            "trend_percentage": round(random.uniform(-10, 15), 1),
        },
    }


# =============================================================================
# SYNCHRONOUS WRAPPERS (for tools that need sync interface)
# =============================================================================


def search_products_sync(
    query: str,
    category: Literal["electronics", "clothing", "home", "sports"],
    price_range: PriceRange,
    filters: list[Filter],
    sort_by: str = "relevance",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Synchronous wrapper for search_products_impl."""
    return asyncio.get_event_loop().run_until_complete(
        search_products_impl(query, category, price_range, filters, sort_by, limit)
    )


def create_order_sync(
    customer_id: str,
    items: list[OrderItem],
    shipping_address: ShippingAddress,
    payment_method: Literal["credit_card", "paypal", "bank_transfer"],
    coupon_code: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for create_order_impl."""
    return asyncio.get_event_loop().run_until_complete(
        create_order_impl(customer_id, items, shipping_address, payment_method, coupon_code)
    )


def get_analytics_sync(
    metric_type: Literal["sales", "traffic", "conversion"],
    date_range: DateRange,
    granularity: Literal["hour", "day", "week", "month"],
    dimensions: list[str],
) -> dict[str, Any]:
    """Synchronous wrapper for get_analytics_impl."""
    return asyncio.get_event_loop().run_until_complete(
        get_analytics_impl(metric_type, date_range, granularity, dimensions)
    )


# =============================================================================
# TASK DEFINITION
# =============================================================================

COMPLEX_TASK = """I want to buy a new laptop for programming. Search for laptops under $1500 with \
at least 16GB RAM. Then create an order for the best option, shipping to \
123 Main St, San Francisco, CA 94102, USA. Use my credit card. My customer ID is CUST-12345. \
Finally, show me the sales analytics for electronics this month."""
