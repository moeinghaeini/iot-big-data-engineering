package com.bosch.iot.sensor.batch

import org.apache.spark.sql.{SparkSession, DataFrame}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/**
 * Batch Processing Job for Automotive Sensor Data Analytics
 * Performs daily/weekly analytics on sensor data stored in HDFS/Hive
 */
object SensorDataAnalytics {
  
  def main(args: Array[String]): Unit = {
    
    // Configuration
    val inputPath = sys.env.getOrElse("INPUT_PATH", "/data/sensor-raw")
    val outputPath = sys.env.getOrElse("OUTPUT_PATH", "/data/sensor-analytics")
    val processingDate = sys.env.getOrElse("PROCESSING_DATE", LocalDate.now().toString)
    val analyticsType = sys.env.getOrElse("ANALYTICS_TYPE", "daily") // daily, weekly, monthly
    
    // Create Spark Session
    val spark = SparkSession.builder()
      .appName(s"SensorDataAnalytics-$analyticsType")
      .config("spark.sql.adaptive.enabled", "true")
      .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
      .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
      .enableHiveSupport()
      .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    try {
      // Load sensor data
      val sensorDF = loadSensorData(spark, inputPath, processingDate, analyticsType)
      
      if (sensorDF.count() > 0) {
        // Perform various analytics
        val dailyAnalytics = performDailyAnalytics(sensorDF)
        val sensorTypeAnalytics = performSensorTypeAnalytics(sensorDF)
        val vehicleAnalytics = performVehicleAnalytics(sensorDF)
        val qualityAnalytics = performQualityAnalytics(sensorDF)
        val anomalyAnalytics = performAnomalyAnalytics(sensorDF)
        
        // Write results
        writeAnalyticsResults(
          dailyAnalytics, 
          sensorTypeAnalytics, 
          vehicleAnalytics, 
          qualityAnalytics, 
          anomalyAnalytics, 
          outputPath, 
          processingDate
        )
        
        // Generate reports
        generateReports(spark, outputPath, processingDate)
        
        println(s"Batch analytics completed successfully for date: $processingDate")
      } else {
        println(s"No data found for processing date: $processingDate")
      }
      
    } catch {
      case e: Exception =>
        println(s"Error in batch analytics: ${e.getMessage}")
        e.printStackTrace()
        sys.exit(1)
    } finally {
      spark.stop()
    }
  }
  
  /**
   * Load sensor data from storage
   */
  def loadSensorData(spark: SparkSession, inputPath: String, processingDate: String, analyticsType: String): DataFrame = {
    
    val dateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")
    val date = LocalDate.parse(processingDate, dateFormatter)
    
    val path = analyticsType match {
      case "daily" => s"$inputPath/year=${date.getYear}/month=${date.getMonthValue}/day=${date.getDayOfMonth}"
      case "weekly" => s"$inputPath/year=${date.getYear}/week=${date.getDayOfYear / 7}"
      case "monthly" => s"$inputPath/year=${date.getYear}/month=${date.getMonthValue}"
      case _ => s"$inputPath/date=$processingDate"
    }
    
    println(s"Loading data from: $path")
    
    spark.read
      .option("multiline", "true")
      .json(path)
      .withColumn("processing_date", lit(processingDate))
  }
  
  /**
   * Perform daily analytics
   */
  def performDailyAnalytics(df: DataFrame): DataFrame = {
    df.groupBy("processing_date", "sensorType")
      .agg(
        count("*").alias("total_records"),
        countDistinct("vehicleId").alias("unique_vehicles"),
        countDistinct("sensorId").alias("unique_sensors"),
        min("timestamp").alias("first_record"),
        max("timestamp").alias("last_record"),
        avg("quality_score").alias("avg_quality_score"),
        stddev("quality_score").alias("quality_stddev")
      )
      .withColumn("analytics_type", lit("daily"))
      .withColumn("generated_at", current_timestamp())
  }
  
  /**
   * Perform sensor type specific analytics
   */
  def performSensorTypeAnalytics(df: DataFrame): DataFrame = {
    df.groupBy("processing_date", "sensorType")
      .agg(
        count("*").alias("record_count"),
        // Radar specific metrics
        when(col("sensorType") === "radar", 
          avg(col("measurements.distance").cast(DoubleType))).alias("avg_distance"),
        when(col("sensorType") === "radar", 
          max(col("measurements.distance").cast(DoubleType))).alias("max_distance"),
        when(col("sensorType") === "radar", 
          min(col("measurements.distance").cast(DoubleType))).alias("min_distance"),
        
        // Camera specific metrics
        when(col("sensorType") === "camera", 
          avg(col("measurements.object_count").cast(IntegerType))).alias("avg_object_count"),
        when(col("sensorType") === "camera", 
          max(col("measurements.object_count").cast(IntegerType))).alias("max_object_count"),
        
        // GPS specific metrics
        when(col("sensorType") === "gps", 
          avg(col("measurements.speed").cast(DoubleType))).alias("avg_speed"),
        when(col("sensorType") === "gps", 
          max(col("measurements.speed").cast(DoubleType))).alias("max_speed"),
        
        // IMU specific metrics
        when(col("sensorType") === "imu", 
          avg(col("measurements.acceleration.x").cast(DoubleType))).alias("avg_acceleration_x"),
        when(col("sensorType") === "imu", 
          avg(col("measurements.acceleration.y").cast(DoubleType))).alias("avg_acceleration_y"),
        when(col("sensorType") === "imu", 
          avg(col("measurements.acceleration.z").cast(DoubleType))).alias("avg_acceleration_z")
      )
      .withColumn("analytics_type", lit("sensor_type"))
      .withColumn("generated_at", current_timestamp())
  }
  
  /**
   * Perform vehicle specific analytics
   */
  def performVehicleAnalytics(df: DataFrame): DataFrame = {
    df.groupBy("processing_date", "vehicleId")
      .agg(
        count("*").alias("total_sensor_readings"),
        countDistinct("sensorType").alias("sensor_types_used"),
        countDistinct("sensorId").alias("unique_sensors"),
        avg("quality_score").alias("avg_quality_score"),
        min("timestamp").alias("first_reading"),
        max("timestamp").alias("last_reading"),
        // Calculate data coverage
        (max(unix_timestamp(col("timestamp"))) - min(unix_timestamp(col("timestamp")))).alias("coverage_seconds")
      )
      .withColumn("analytics_type", lit("vehicle"))
      .withColumn("generated_at", current_timestamp())
  }
  
  /**
   * Perform data quality analytics
   */
  def performQualityAnalytics(df: DataFrame): DataFrame = {
    df.groupBy("processing_date")
      .agg(
        count("*").alias("total_records"),
        count(when(col("quality_score") >= 0.8, 1)).alias("high_quality_records"),
        count(when(col("quality_score") >= 0.6 && col("quality_score") < 0.8, 1)).alias("medium_quality_records"),
        count(when(col("quality_score") < 0.6, 1)).alias("low_quality_records"),
        avg("quality_score").alias("avg_quality_score"),
        min("quality_score").alias("min_quality_score"),
        max("quality_score").alias("max_quality_score"),
        stddev("quality_score").alias("quality_stddev")
      )
      .withColumn("quality_percentage", 
        (col("high_quality_records") / col("total_records") * 100).cast(DecimalType(5, 2)))
      .withColumn("analytics_type", lit("quality"))
      .withColumn("generated_at", current_timestamp())
  }
  
  /**
   * Perform anomaly analytics
   */
  def performAnomalyAnalytics(df: DataFrame): DataFrame = {
    df.filter(col("anomaly_score") > 0)
      .groupBy("processing_date", "sensorType")
      .agg(
        count("*").alias("anomaly_count"),
        avg("anomaly_score").alias("avg_anomaly_score"),
        max("anomaly_score").alias("max_anomaly_score"),
        countDistinct("vehicleId").alias("affected_vehicles"),
        countDistinct("sensorId").alias("affected_sensors")
      )
      .withColumn("analytics_type", lit("anomaly"))
      .withColumn("generated_at", current_timestamp())
  }
  
  /**
   * Write analytics results to storage
   */
  def writeAnalyticsResults(
    dailyAnalytics: DataFrame,
    sensorTypeAnalytics: DataFrame,
    vehicleAnalytics: DataFrame,
    qualityAnalytics: DataFrame,
    anomalyAnalytics: DataFrame,
    outputPath: String,
    processingDate: String
  ): Unit = {
    
    // Write daily analytics
    dailyAnalytics.write
      .mode("overwrite")
      .option("path", s"$outputPath/daily-analytics/date=$processingDate")
      .saveAsTable("sensor_daily_analytics")
    
    // Write sensor type analytics
    sensorTypeAnalytics.write
      .mode("overwrite")
      .option("path", s"$outputPath/sensor-type-analytics/date=$processingDate")
      .saveAsTable("sensor_type_analytics")
    
    // Write vehicle analytics
    vehicleAnalytics.write
      .mode("overwrite")
      .option("path", s"$outputPath/vehicle-analytics/date=$processingDate")
      .saveAsTable("sensor_vehicle_analytics")
    
    // Write quality analytics
    qualityAnalytics.write
      .mode("overwrite")
      .option("path", s"$outputPath/quality-analytics/date=$processingDate")
      .saveAsTable("sensor_quality_analytics")
    
    // Write anomaly analytics
    if (anomalyAnalytics.count() > 0) {
      anomalyAnalytics.write
        .mode("overwrite")
        .option("path", s"$outputPath/anomaly-analytics/date=$processingDate")
        .saveAsTable("sensor_anomaly_analytics")
    }
  }
  
  /**
   * Generate summary reports
   */
  def generateReports(spark: SparkSession, outputPath: String, processingDate: String): Unit = {
    
    // Generate summary report
    val summaryReport = spark.sql(s"""
      SELECT 
        '$processingDate' as report_date,
        'Daily Summary Report' as report_type,
        COUNT(*) as total_records,
        COUNT(DISTINCT vehicleId) as unique_vehicles,
        COUNT(DISTINCT sensorId) as unique_sensors,
        COUNT(DISTINCT sensorType) as sensor_types,
        AVG(quality_score) as avg_quality,
        COUNT(CASE WHEN anomaly_score > 0 THEN 1 END) as anomaly_count
      FROM sensor_quality_checked
      WHERE processing_date = '$processingDate'
    """)
    
    summaryReport.write
      .mode("overwrite")
      .option("path", s"$outputPath/reports/summary/date=$processingDate")
      .saveAsTable("sensor_summary_report")
    
    // Generate sensor type distribution report
    val sensorTypeReport = spark.sql(s"""
      SELECT 
        '$processingDate' as report_date,
        sensorType,
        COUNT(*) as record_count,
        COUNT(DISTINCT vehicleId) as unique_vehicles,
        AVG(quality_score) as avg_quality
      FROM sensor_quality_checked
      WHERE processing_date = '$processingDate'
      GROUP BY sensorType
      ORDER BY record_count DESC
    """)
    
    sensorTypeReport.write
      .mode("overwrite")
      .option("path", s"$outputPath/reports/sensor-type/date=$processingDate")
      .saveAsTable("sensor_type_report")
    
    println("Reports generated successfully")
  }
}
