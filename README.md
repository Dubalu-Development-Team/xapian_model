# xapian_model

A generic Python ORM-like base class for building models backed by [Xapiand](https://github.com/pber/xapiand), a distributed search engine. Part of the Dubalu Framework.

## Features

- **Fully async** — All Xapiand operations use `async`/`await` (powered by `pyxapiand>=2.1.0` and `httpx`).
- **BaseXapianModel** — Base class with attribute interception, save/delete operations, and template-based dynamic index naming.
- **Manager** — Descriptor-based manager providing `create()`, `get()`, and `filter()` query methods.
- **SearchResults** — Dataclass wrapping search results with total counts and aggregations.
- **Schema auto-provisioning** — Automatically provisions the schema on first write.

## Installation

```bash
pip install xapian-model
```

### Dependencies

Requires [pyxapiand](https://github.com/Dubalu-Development-Team/xapiand) 2.1.0+ (async client):

```bash
pip install "pyxapiand>=2.1.0"
```

## Quick Start

```python
import asyncio
from xapian_model.base import BaseXapianModel

class Product(BaseXapianModel):
    INDEX_TEMPLATE = "products/{store_id}"
    SCHEMA = {
        "name": {"_type": "text"},
        "price": {"_type": "float"},
        "active": {"_type": "boolean", "_default": True},
    }

async def main():
    # Create a product
    product = await Product.objects.create(store_id="store1", name="Widget", price=9.99)

    # Retrieve by ID
    product = await Product.objects.get(id="abc123", store_id="store1")

    # Search
    results = await Product.objects.filter(query="widget", store_id="store1", limit=10)
    for item in results.results:
        print(item.name, item.price)

    # Update and save
    product.price = 12.99
    await product.save()

    # Delete
    await product.delete()

asyncio.run(main())
```

## Requirements

- Python 3.12+
- [pyxapiand](https://github.com/Dubalu-Development-Team/xapiand) >= 2.1.0
- [Xapiand](https://github.com/pber/xapiand) server

## License

[MIT](LICENSE) — Copyright (c) 2026 Dubalu International
