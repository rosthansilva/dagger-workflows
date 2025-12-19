# Bazel Tests Examples

This is a Bazel workspace that contains examples for the blogpost about tests.

The `example` directory contains the most basic examples with explicit loads and uses rules for scala and java directly.

The `example-with-config` leverages more advanced setup, using `unit_test` and `integration_test` functions defined in
`tools/build_rules` as well as prelude to avoid load statements. Common test utils for unit and integration tests that
are automatically added to deps are defined in `test-utils` directory.