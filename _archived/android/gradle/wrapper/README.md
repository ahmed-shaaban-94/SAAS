# Gradle Wrapper JAR

The `gradle-wrapper.jar` binary is not checked in to reduce repo size.
To generate it, run from the `android/` directory:

```bash
# If you have Gradle installed locally:
gradle wrapper --gradle-version 8.11.1

# Or download directly:
curl -L -o gradle/wrapper/gradle-wrapper.jar https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar
```

After generating, the project will build normally with `./gradlew build`.
