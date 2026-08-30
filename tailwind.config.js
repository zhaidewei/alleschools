/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./view_xy.html"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        display: ["Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"]
      },
      colors: {
        canvas: "#f7f3eb",
        forest: "#173f35",
        terracotta: "#a8462b",
        moss: "#6f8a58",
        ochre: "#c08a3e",
        berry: "#8f5063",
        ink: "#102a24"
      }
    }
  },
  plugins: []
};
