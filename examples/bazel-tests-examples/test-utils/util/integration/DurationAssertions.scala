package util.integration


object DurationAssertions {
    def assertDuration(expectedMs: Int)(block: => Unit): Unit = {
        val start = System.currentTimeMillis()
        block
        val end = System.currentTimeMillis()
        val duration = end - start
        assert(duration <= expectedMs)
    }
}