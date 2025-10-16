package com.bosch.iot.sensor

import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.streaming.{StreamingContext, Seconds}
import org.apache.spark.streaming.kafka010.{ConsumerStrategies, KafkaUtils, LocationStrategies}
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.clients.consumer.ConsumerConfig
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import scala.util.{Try, Success, Failure}
import java.time.Instant
import java.time.format.DateTimeFormatter

/**
 * Spark Streaming Job for Real-time Automotive Sensor Data Processing
 * Processes sensor data from Kafka and performs real-time analytics
 */
object SensorDataProcessor {
  
  def main(args: Array[String]): Unit = {
    
    // Configuration
    val kafkaBootstrapServers = sys.env.getOrElse("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    val kafkaTopic = sys.env.getOrElse("KAFKA_TOPIC", "sensor-data")
    val kafkaGroupId = sys.env.getOrElse("KAFKA_GROUP_ID", "sensor-processor-group")
    val checkpointDir = sys.env.getOrElse("CHECKPOINT_DIR", "/tmp/spark-checkpoint")
    val outputPath = sys.env.getOrElse("OUTPUT_PATH", "/tmp/sensor-processed")
    val batchInterval = sys.env.getOrElse("BATCH_INTERVAL", "10").toInt
    
    // Create Spark Session
    val spark = SparkSession.builder()
      .appName("SensorDataProcessor")
      .config("spark.sql.adaptive.enabled", "true")
      .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
      .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
      .config("spark.sql.streaming.checkpointLocation", checkpointDir)
      .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    // Create Streaming Context
    val ssc = new StreamingContext(spark.sparkContext, Seconds(batchInterval))
    
    // Kafka consumer configuration
    val kafkaParams = Map[String, Object](
      ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG -> kafkaBootstrapServers,
      ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG -> classOf[StringDeserializer],
      ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG -> classOf[StringDeserializer],
      ConsumerConfig.GROUP_ID_CONFIG -> kafkaGroupId,
      ConsumerConfig.AUTO_OFFSET_RESET_CONFIG -> "latest",
      ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG -> (false: java.lang.Boolean)
    )
    
    val topics = Array(kafkaTopic)
    
    // Create Kafka stream
    val kafkaStream = KafkaUtils.createDirectStream[String, String](
      ssc,
      LocationStrategies.PreferConsistent,
      ConsumerStrategies.Subscribe[String, String](topics, kafkaParams)
    )
    
    // Process the stream
    kafkaStream.foreachRDD { rdd =>
      if (!rdd.isEmpty()) {
        processSensorData(rdd.map(_.value()), spark, outputPath)
      }
    }
    
    // Start streaming
    ssc.start()
    ssc.awaitTermination()
  }
  
  /**
   * Process sensor data RDD
   */
  def processSensorData(rdd: org.apache.spark.rdd.RDD[String], spark: SparkSession, outputPath: String): Unit = {
    
    import spark.implicits._
    
    // Define schema for sensor data
    val sensorSchema = StructType(Seq(
      StructField("timestamp", StringType, nullable = false),
      StructField("sensorId", StringType, nullable = false),
      StructField("vehicleId", StringType, nullable = false),
      StructField("sensorType", StringType, nullable = false),
      StructField("location", StructType(Seq(
        StructField("latitude", DoubleType, nullable = false),
        StructField("longitude", DoubleType, nullable = false)
      )), nullable = false),
      StructField("measurements", MapType(StringType, StringType), nullable = false),
      StructField("metadata", MapType(StringType, StringType), nullable = false)
    ))
    
    try {
      // Parse JSON and create DataFrame
      val sensorDF = rdd.map { jsonString =>
        Try {
          val mapper = new ObjectMapper()
          mapper.registerModule(DefaultScalaModule)
          mapper.readValue(jsonString, classOf[Map[String, Any]])
        } match {
          case Success(data) => data
          case Failure(exception) =>
            println(s"Failed to parse JSON: $jsonString, Error: ${exception.getMessage}")
            Map.empty[String, Any]
        }
      }.filter(_.nonEmpty)
        .toDF()
      
      if (sensorDF.count() > 0) {
        // Data Quality Checks
        val qualityCheckedDF = performDataQualityChecks(sensorDF)
        
        // Real-time Analytics
        val analyticsDF = performRealTimeAnalytics(qualityCheckedDF)
        
        // Anomaly Detection
        val anomalyDF = detectAnomalies(qualityCheckedDF)
        
        // Write to storage
        writeToStorage(qualityCheckedDF, analyticsDF, anomalyDF, outputPath)
        
        // Print metrics
        printMetrics(qualityCheckedDF, analyticsDF, anomalyDF)
      }
      
    } catch {
      case e: Exception =>
        println(s"Error processing sensor data: ${e.getMessage}")
        e.printStackTrace()
    }
  }
  
  /**
   * Perform data quality checks
   */
  def performDataQualityChecks(df: DataFrame): DataFrame = {
    df.filter(
      col("timestamp").isNotNull &&
      col("sensorId").isNotNull &&
      col("vehicleId").isNotNull &&
      col("sensorType").isNotNull &&
      col("location").isNotNull
    ).withColumn("quality_score", 
      when(col("timestamp").isNotNull, 1.0).otherwise(0.0) +
      when(col("sensorId").isNotNull, 1.0).otherwise(0.0) +
      when(col("vehicleId").isNotNull, 1.0).otherwise(0.0) +
      when(col("sensorType").isNotNull, 1.0).otherwise(0.0) +
      when(col("location").isNotNull, 1.0).otherwise(0.0)
    ).withColumn("processing_timestamp", current_timestamp())
  }
  
  /**
   * Perform real-time analytics
   */
  def performRealTimeAnalytics(df: DataFrame): DataFrame = {
    df.groupBy("sensorType", window(col("timestamp"), "1 minute"))
      .agg(
        count("*").alias("record_count"),
        countDistinct("vehicleId").alias("unique_vehicles"),
        countDistinct("sensorId").alias("unique_sensors"),
        avg("quality_score").alias("avg_quality_score")
      )
      .withColumn("processing_timestamp", current_timestamp())
  }
  
  /**
   * Detect anomalies in sensor data
   */
  def detectAnomalies(df: DataFrame): DataFrame = {
    // Simple anomaly detection based on sensor type
    df.withColumn("anomaly_score", 
      when(col("sensorType") === "radar" && 
           col("measurements.distance").cast(DoubleType) > 200, 1.0)
      .when(col("sensorType") === "camera" && 
            col("measurements.object_count").cast(IntegerType) > 20, 1.0)
      .when(col("sensorType") === "gps" && 
            col("measurements.speed").cast(DoubleType) > 200, 1.0)
      .otherwise(0.0)
    ).filter(col("anomaly_score") > 0)
     .withColumn("processing_timestamp", current_timestamp())
  }
  
  /**
   * Write processed data to storage
   */
  def writeToStorage(qualityDF: DataFrame, analyticsDF: DataFrame, anomalyDF: DataFrame, outputPath: String): Unit = {
    
    val timestamp = DateTimeFormatter.ofPattern("yyyy-MM-dd-HH-mm-ss").format(Instant.now())
    
    // Write quality checked data
    qualityDF.write
      .mode("append")
      .option("path", s"$outputPath/quality-checked")
      .saveAsTable("sensor_quality_checked")
    
    // Write analytics data
    analyticsDF.write
      .mode("append")
      .option("path", s"$outputPath/analytics")
      .saveAsTable("sensor_analytics")
    
    // Write anomaly data
    if (anomalyDF.count() > 0) {
      anomalyDF.write
        .mode("append")
        .option("path", s"$outputPath/anomalies")
        .saveAsTable("sensor_anomalies")
    }
  }
  
  /**
   * Print processing metrics
   */
  def printMetrics(qualityDF: DataFrame, analyticsDF: DataFrame, anomalyDF: DataFrame): Unit = {
    val qualityCount = qualityDF.count()
    val analyticsCount = analyticsDF.count()
    val anomalyCount = anomalyDF.count()
    
    println(s"=== Processing Metrics ===")
    println(s"Quality Checked Records: $qualityCount")
    println(s"Analytics Records: $analyticsCount")
    println(s"Anomaly Records: $anomalyCount")
    println(s"Processing Time: ${Instant.now()}")
    println("=========================")
  }
}
