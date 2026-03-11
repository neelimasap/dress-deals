# Data Format

The main dataset is stored in `data/deals.json`.

## Shape

```text
brands[]
  items[]
    id
    name
    silhouette
    material
    imageUrl
    stores[]
    history[]
```

## Root Fields

- `lastUpdated`
- `currency`
- `brands`

## Store Fields

- `name`
- `price`
- `originalPrice`
- `url`
- `imageUrl`
- `updatedAt`

## History Fields

- `date`
- `price`
