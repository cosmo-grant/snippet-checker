# frozen_string_literal: true

h = { a: [1] }
vals = h.values
h[:a].push(2)
h[:b] = 3
vals.each { |v| p v }
