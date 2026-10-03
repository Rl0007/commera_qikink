export const variantLabel = (row) => [row.colour, row.size].filter(Boolean).join(' / ') || row.item_name || row.item_code

export const modeLabel = (row) => (row.plain_product ? 'Plain' : 'My Products')
