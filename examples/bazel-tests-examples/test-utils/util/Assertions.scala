package util


object Assertions {
    def assertLength[A](a: List[A], expected: Int): Unit = {
        assert(a.length == expected)
    }
}