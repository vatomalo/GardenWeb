'use strict';
window.GARDEN_WEORDER = Object.freeze({
  storefrontUrl: 'https://order.weorder.com/app/garden',
  // Enable only after WeOrder documents a postMessage from its embedded
  // storefront with the exact shape {type: completionType, orderId: string}.
  completionType: null
});
