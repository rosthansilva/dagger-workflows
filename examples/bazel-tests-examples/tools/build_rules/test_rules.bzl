load("@io_bazel_rules_scala//scala:scala.bzl", "scala_test")

def unit_test(**kwargs):
    _setup_test_attributes(kwargs, size="small", tag="unit", extra_deps=["//test-utils/util"])
    return scala_test(**kwargs)


def integration_test(**kwargs):
    _setup_test_attributes(kwargs, size="medium", tag="integration", extra_deps=["//test-utils/util", "//test-utils/util/integration"])
    return scala_test(**kwargs)


# common method that adjusts kwargs (mutable)
def _setup_test_attributes(kwargs, size, tag, extra_deps):
    if "name" not in kwargs:
        kwargs["name"] = _default_target_name() 

    if "srcs" not in kwargs:
        kwargs["srcs"] = native.glob(["*.scala"])

    if "size" not in kwargs:
        kwargs["size"] = size

    if "tags" not in kwargs:
        kwargs["tags"] = []
    if tag not in kwargs["tags"]:
        kwargs["tags"].append(tag)

    if "deps" not in kwargs:
        kwargs["deps"] = []
    for dep in extra_deps:
        if dep not in kwargs["deps"]:
            kwargs["deps"].append(dep)


def _default_target_name():
    _, _, target_name = native.package_name().rpartition("/")
    return target_name