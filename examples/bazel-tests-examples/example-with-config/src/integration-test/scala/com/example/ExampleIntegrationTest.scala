package com.example

import org.scalatest.funsuite.AnyFunSuite
import util.integration.DurationAssertions
import scala.util.Random

class ExampleIntegrationTest extends AnyFunSuite {
  test("example") {
    val extraMs = if (Random.nextBoolean()) 200 else 0
    DurationAssertions.assertDuration(5000 + extraMs) {
      Thread.sleep(5000)
    }
  }
}
