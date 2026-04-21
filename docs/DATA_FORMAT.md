# Data Format

The main dataset is stored in `data/deals.json`.

## Shape

```text
brand
lastUpdated
items[]
  id
  name
  imageUrl
  releaseYear
  firstSeen
  cheapestStore
  cheapestPrice
  offers[]
  history[]
  storeHistory[]
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
- `store`
- `originalPrice`

## Store History Fields

- `date`
- `store`
- `price`
- `originalPrice`
- `url`
