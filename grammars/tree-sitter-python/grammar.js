module.exports = grammar({
  name: 'python',

  extras: $ => [
    /[ \t\r\n]+/,
    $.comment,
  ],

  rules: {
    module: $ => repeat($._statement),

    _statement: $ => choice(
      $.expression_statement,
      $.assignment,
    ),

    expression_statement: $ => $.expression,

    assignment: $ => seq(
      field('left', $.identifier),
      '=',
      field('right', $.expression),
    ),

    expression: $ => choice(
      $.identifier,
      $.integer,
      $.string,
    ),

    identifier: _ => /[A-Za-z_][A-Za-z0-9_]*/,
    integer: _ => /[0-9]+/,
    string: _ => /"[^"\\n]*"|'[^'\\n]*'/,
    comment: _ => /#[^\n]*/,
  },
});
