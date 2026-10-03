// Benign "real" functionality — the cover that makes the package look useful.
module.exports.slugify = (s) => String(s).toLowerCase().trim().replace(/\s+/g, '-');
