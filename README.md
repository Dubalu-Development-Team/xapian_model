# xapian_model

A generic Python ORM-like base class for building models backed by [Xapiand](https://github.com/pber/xapiand), a distributed search engine. Part of the Dubalu Framework.

## Features

- **BaseXapianModel** — Base class with attribute interception, save/delete operations, and template-based dynamic index naming.
- **Manager** — Descriptor-based manager providing `create()`, `get()`, and `filter()` query methods.
- **SearchResults** — Dataclass wrapping search results with total counts and aggregations.
- **Schema auto-provisioning** — Automatically provisions the schema on first write.

## Installation

```bash
pip install xapian-model
```

### Dependencies

Install the [pyxapiand](https://github.com/Dubalu-Development-Team/xapiand) client library:

```bash
pip install pyxapiand
```

## Quick Start

```python
from xapian_model.base import BaseXapianModel

class Product(BaseXapianModel):
    INDEX_TEMPLATE = "products/{store_id}"
    SCHEMA = {
        "name": {"_type": "text"},
        "price": {"_type": "float"},
        "active": {"_type": "boolean", "_default": True},
    }

# Create a product
product = Product.objects.create(store_id="store1", name="Widget", price=9.99)

# Retrieve by ID
product = Product.objects.get(id="abc123", store_id="store1")

# Search
results = Product.objects.filter(query="widget", store_id="store1", limit=10)
for item in results.results:
    print(item.name, item.price)

# Update and save
product.price = 12.99
product.save()

# Delete
product.delete()
```

## Requirements

- Python 3.12+
- [Xapiand](https://github.com/pber/xapiand) server and client library

## License

[MIT](LICENSE) — Copyright (c) 2026 Dubalu International
