package com.example

import org.scalatest.funsuite.AnyFunSuite
import com.exampale.Calculator

class ExampleTest extends AnyFunSuite {
  test("example") {
    assert(Calculator.add(1, 2) == 3)
  }
}
