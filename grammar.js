/**
 * @file A Tree-Sitter grammar for parsing lsd cli output
 * @author Bullish-Design <bullishdesignllc@gmail.com>
 * @license MIT
 */

/// <reference types="tree-sitter-cli/dsl" />
// @ts-check

module.exports = grammar({
  name: "lsd",

  rules: {
    // TODO: add the actual grammar rules
    source_file: $ => "hello"
  }
});
