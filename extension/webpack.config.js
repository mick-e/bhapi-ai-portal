const path = require("path");
const CopyWebpackPlugin = require("copy-webpack-plugin");

module.exports = (env, argv) => {
  const isProduction = argv.mode === "production";

  return {
    entry: {
      "background/service-worker": "./src/background/service-worker.ts",
      "content/monitor": "./src/content/monitor.ts",
      "popup/popup": "./src/popup/popup.ts",
    },
    output: {
      path: path.resolve(__dirname, "dist"),
      filename: "[name].js",
      clean: true,
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: "ts-loader",
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ["style-loader", "css-loader"],
        },
      ],
    },
    resolve: {
      extensions: [".ts", ".js"],
    },
    plugins: [
      new CopyWebpackPlugin({
        patterns: [
          {
            from: "manifest.json",
            to: "manifest.json",
          },
          {
            from: "src/popup/popup.html",
            to: "popup/popup.html",
          },
          {
            from: "src/popup/popup.css",
            to: "popup/popup.css",
            noErrorOnMissing: true,
          },
          {
            // Placeholder icons directory — replace with real icons before publishing
            from: "icons",
            to: "icons",
            noErrorOnMissing: true,
          },
        ],
      }),
    ],
    devtool: isProduction ? false : "inline-source-map",
    optimization: {
      minimize: isProduction,
    },
  };
};
