const path = require("path");

module.exports = function (options) {
  return {
    ...options,
    resolve: {
      ...options.resolve,
      alias: {
        ...(options.resolve && options.resolve.alias),
        "@workspace/db": path.resolve(__dirname, "../../lib/db/src/index.ts"),
        "@workspace/api-zod": path.resolve(__dirname, "../../lib/api-zod/src/index.ts"),
      },
    },
  };
};
