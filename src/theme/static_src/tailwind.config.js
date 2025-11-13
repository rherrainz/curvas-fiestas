/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../templates/**/*.html",
    "../../**/templates/**/*.html",
  ],

  theme: {
    extend: {},
  },

  plugins: [require("daisyui")],

  daisyui: {
    styled: true,
    themes: [
      {
        "la-navidad": {
          "primary": "#B33643",
          "primary-focus": "#8D2A35",
          "primary-content": "#ffffff",

          "secondary": "#2E5C4B",
          "secondary-focus": "#264A3D",
          "secondary-content": "#ffffff",

          "accent": "#C8A95E",
          "accent-focus": "#B2934E",
          "accent-content": "#1F1F1F",

          "neutral": "#1F1F1F",
          "neutral-content": "#F6F2E8",

          "base-100": "#F6F2E8",
          "base-200": "#EAE6DA",
          "base-300": "#DDD6C6",

          "info": "#2E5C4B",
          "success": "#2E5C4B",
          "warning": "#C8A95E",
          "error": "#B33643",
        }
      },

      "light",  // fallback
    ],
  },
};
