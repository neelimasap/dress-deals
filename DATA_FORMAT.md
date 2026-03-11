# Data Format

The main dataset is stored in `data/deals.json`.

## Shape

```text
<<<<<<< HEAD
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
=======
brands[]
  items[]
    id
    name
    silhouette
    material
    imageUrl
    stores[]
    history[]
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3
```

## Root Fields

<<<<<<< HEAD
- `brand`
- `lastUpdated`
- `items`

## Offer Fields
=======
- `lastUpdated`
- `currency`
- `brands`

## Store Fields
>>>>>>> 7cac992bb87289d5a5c4636070be74c4a79b99d3

- `name`
- `price`
- `originalPrice`
- `url`
- `imageUrl`
- `updatedAt`

## History Fields

- `date`
- `price`
