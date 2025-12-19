package com.example;

import org.junit.Test;
import org.junit.Assert;
import com.exampale.Calculator;

import java.io.IOException;
import java.net.URISyntaxException;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.stream.Collectors;

public class ExampleTest {


    @Test public void advancedResourcesUsage() throws URISyntaxException, IOException {
        // Path to the empty directory that Bazel prepared for this test target
        var testWorkspace = Paths.get(System.getenv("TEST_TMPDIR"));

        // Path to resources used in this test (as it is inside the jar file)
        var resourcesPath = "/examples";

        // Find URI of the resources directory inside the jar file
        var uri = getClass().getResource(resourcesPath).toURI();

        // Create a new file system for the jar file based on URI
        var jarFs = FileSystems.newFileSystem(uri, new HashMap<>());

        // Copy all files from the jar file to the test workspace
        var paths = Files.list(jarFs.getPath(resourcesPath)).toList();
        for (var source : paths) {
            // Note that Path objects determine the file system that they belong to
            var target = testWorkspace.resolve(source.getFileName().toString());
            Files.copy(source, target);
        }

        var copiedFiles = Files.list(testWorkspace).count();
        Assert.assertEquals(copiedFiles, 3);
    }

    @Test public void calculatorTest() {
        Assert.assertEquals(Calculator.add(1, 2), 3);
    }
}