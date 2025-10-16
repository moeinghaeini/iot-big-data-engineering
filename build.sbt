name := "iot-big-data-engineering"

version := "1.0.0"

scalaVersion := "2.12.15"

organization := "com.bosch.iot"

// Spark dependencies
val sparkVersion = "3.3.0"
val kafkaVersion = "3.3.1"
val jacksonVersion = "2.13.4"

libraryDependencies ++= Seq(
  // Spark Core
  "org.apache.spark" %% "spark-core" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-sql" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-streaming" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-streaming-kafka-0-10" % sparkVersion,
  
  // Kafka
  "org.apache.kafka" % "kafka-clients" % kafkaVersion,
  "org.apache.kafka" %% "kafka" % kafkaVersion,
  
  // JSON Processing
  "com.fasterxml.jackson.core" % "jackson-core" % jacksonVersion,
  "com.fasterxml.jackson.core" % "jackson-databind" % jacksonVersion,
  "com.fasterxml.jackson.module" %% "jackson-module-scala" % jacksonVersion,
  
  // Database connectors
  "org.postgresql" % "postgresql" % "42.5.1",
  "org.apache.hbase" % "hbase-client" % "2.4.11",
  "org.apache.hbase" % "hbase-common" % "2.4.11",
  
  // Monitoring
  "io.prometheus" % "simpleclient" % "0.16.0",
  "io.prometheus" % "simpleclient_httpserver" % "0.16.0",
  
  // Testing
  "org.scalatest" %% "scalatest" % "3.2.14" % "test",
  "org.apache.spark" %% "spark-sql" % sparkVersion % "test" classifier "tests",
  "org.apache.spark" %% "spark-core" % sparkVersion % "test" classifier "tests"
)

// Assembly plugin for creating fat JARs
assemblyMergeStrategy in assembly := {
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case x => MergeStrategy.first
}

// Exclude provided dependencies from assembly
assemblyExcludedJars in assembly := {
  val cp = (fullClasspath in assembly).value
  cp filter {_.data.getName.contains("spark")}
}

// Scala compiler options
scalacOptions ++= Seq(
  "-deprecation",
  "-encoding", "UTF-8",
  "-feature",
  "-language:existentials",
  "-language:higherKinds",
  "-language:implicitConversions",
  "-unchecked",
  "-Xfatal-warnings",
  "-Xlint",
  "-Yno-adapted-args",
  "-Ywarn-dead-code",
  "-Ywarn-numeric-widen",
  "-Ywarn-value-discard",
  "-Xfuture"
)

// Java compiler options
javacOptions ++= Seq(
  "-source", "11",
  "-target", "11"
)

// Test configuration
testOptions in Test += Tests.Argument("-oF")

// Fork tests to avoid conflicts
fork in Test := true

// Resource management
resourceDirectory in Compile := baseDirectory.value / "src" / "main" / "resources"

// Main class for assembly
mainClass in assembly := Some("com.bosch.iot.sensor.SensorDataProcessor")

// Assembly JAR name
assemblyJarName in assembly := s"${name.value}-${version.value}-assembly.jar"
