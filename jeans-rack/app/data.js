// Everything on the rail lives here. To change a pair, edit its entry.
// `fit` sets the leg shape and `wash` the denim colour; both are used by
// scripts/build_garments.py to make that pair's pictures from the jeans photo.
// Run that script again after changing either, and it writes public/garments/<id>-front.webp
// and <id>-side.webp. `stock` is how many of each waist size are left (0 = sold out).

export const BRAND = {
  line1: "Rinse &",
  line2: "Repeat",
  tagline: "Denim and trousers, hung up and ready.",
  email: "hello@rinseandrepeat.shop",
  currency: "$",
};

export const SIZES = [28, 30, 32, 34, 36];

export const PRODUCTS = [
  {
    id: "straight-light",
    name: "Straight Leg",
    colour: "Light Vintage",
    price: 85,
    fit: "straight",
    wash: "#8fb0d3",
    originalWash: true, // the photo as it is, not re-dyed
    description: "The everyday pair. Sits at the waist, straight through the leg, worn in with a soft vintage wash.",
    stock: { 28: 3, 30: 6, 32: 4, 34: 2, 36: 0 },
  },
  {
    id: "wide-raw",
    name: "Wide Leg",
    colour: "Raw Indigo",
    price: 110,
    fit: "wide",
    wash: "#22335a",
    description: "Deep indigo cut wide from hip to hem. Fades to fit you the more you wear it.",
    stock: { 28: 0, 30: 2, 32: 5, 34: 3, 36: 1 },
  },
  {
    id: "straight-ecru",
    name: "Straight Leg",
    colour: "Ecru",
    price: 95,
    fit: "straight",
    wash: "#e6dcc6",
    description: "Undyed denim, the colour of raw cotton. Straight and a little boxy.",
    stock: { 28: 2, 30: 4, 32: 4, 34: 0, 36: 2 },
  },
  {
    id: "baggy-black",
    name: "Baggy",
    colour: "Washed Black",
    price: 90,
    fit: "baggy",
    wash: "#2a2a2e",
    description: "Low on the hip and loose all the way down. Garment dyed black and washed until it softens.",
    stock: { 28: 5, 30: 5, 32: 1, 34: 4, 36: 3 },
  },
  {
    id: "slim-light",
    name: "Slim Taper",
    colour: "Bleach Wash",
    price: 80,
    fit: "slim",
    wash: "#b9cfe6",
    description: "Room in the thigh, tapered to the ankle. Bleached light for summer.",
    stock: { 28: 4, 30: 0, 32: 3, 34: 2, 36: 0 },
  },
  {
    id: "flare-stone",
    name: "Flare",
    colour: "Stone Wash",
    price: 98,
    fit: "flare",
    wash: "#7d99b8",
    description: "Fitted to the knee, then it kicks out. A seventies shape in a soft stone wash.",
    stock: { 28: 1, 30: 3, 32: 2, 34: 0, 36: 0 },
  },
  {
    id: "relaxed-olive",
    name: "Relaxed Leg",
    colour: "Olive Overdye",
    price: 88,
    fit: "relaxed",
    wash: "#5c6344",
    description: "Blue denim overdyed olive, so the texture still shows through. Easy through the leg.",
    stock: { 28: 3, 30: 4, 32: 6, 34: 4, 36: 2 },
  },
  {
    id: "wide-charcoal",
    name: "Wide Leg",
    colour: "Charcoal",
    price: 100,
    fit: "wide",
    wash: "#4b4c52",
    description: "Grey-black denim with a long wide leg that drapes. Dress it up or wear it with trainers.",
    stock: { 28: 0, 30: 2, 32: 3, 34: 3, 36: 1 },
  },
  {
    id: "barrel-vintage",
    name: "Barrel Leg",
    colour: "Vintage Blue",
    price: 105,
    fit: "barrel",
    wash: "#6a8db4",
    description: "Curved through the knee and narrow at the hem. The shape everyone keeps asking about.",
    stock: { 28: 2, 30: 2, 32: 0, 34: 1, 36: 0 },
  },
];

export function totalStock(product) {
  return Object.values(product.stock).reduce((sum, n) => sum + n, 0);
}
