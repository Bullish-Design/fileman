module.exports = grammar({
  name: 'python',

  extras: $ => [
    /[ \t\r\n]+/,
    $.comment,
  ],

  rules: {
    module: $ => repeat($._statement),

    _statement: $ => choice(
      $.function_definition,
      $.return_statement,
      $.expression_statement,
      $.assignment,
    ),

    function_definition: $ => seq(
      'def',
      field('name', $.identifier),
      field('parameters', $.parameters),
      ':',
      field('body', $.suite),
    ),

    parameters: $ => seq(
      '(',
      optional(seq(
        $.identifier,
        repeat(seq(',', $.identifier)),
        optional(','),
      )),
      ')',
    ),

    suite: $ => choice(
      $.return_statement,
      $.expression_statement,
      $.assignment,
    ),

    return_statement: $ => seq(
      'return',
      $.expression,
    ),

    expression_statement: $ => $.expression,

    assignment: $ => seq(
      field('left', $.identifier),
      '=',
      field('right', $.expression),
    ),

    expression: $ => choice(
      $.binary_expression,
      $.identifier,
      $.integer,
      $.string,
    ),

    binary_expression: $ => prec.left(seq(
      field('left', $.expression),
      field('operator', '+'),
      field('right', $.expression),
    )),

    identifier: _ => /[A-Za-z_][A-Za-z0-9_]*/,
    integer: _ => /[0-9]+/,
    string: _ => /"[^"\\n]*"|'[^'\\n]*'/,
    comment: _ => /#[^\n]*/,
  },
});
