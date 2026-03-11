# Data Format

The main dataset is stored in `data/deals.json`.

## Shape

```text
brand
lastUpdated
items[]
  name
  imageUrl
  releaseYear
  cheapestStore
  cheapestPrice
  offers[]
  history[]
```

## Root Fields

- `brand`
- `lastUpdated`
- `items`

## Offer Fields

- `name`
- `price`
- `originalPrice`
- `url`
- `imageUrl`
- `updatedAt`

## History Fields

- `date`
- `price`
