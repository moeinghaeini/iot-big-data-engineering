package com.bosch.iot.sensor

import java.util.Properties
import java.util.concurrent.Future
import org.apache.kafka.clients.producer.{KafkaProducer, ProducerRecord, RecordMetadata, Callback}
import org.apache.kafka.common.serialization.StringSerializer
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.databind.SerializationFeature
import scala.util.{Try, Success, Failure}
import scala.concurrent.{Future => ScalaFuture, Promise}
import scala.concurrent.ExecutionContext.Implicits.global

/**
 * Kafka Producer for Automotive Sensor Data
 * Handles high-throughput streaming of sensor data to Kafka topics
 */
class SensorDataProducer(bootstrapServers: String, topicName: String) {
  
  private val objectMapper = new ObjectMapper()
    .registerModule(DefaultScalaModule)
    .configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false)
  
  private val producer = createProducer()
  
  private def createProducer(): KafkaProducer[String, String] = {
    val props = new Properties()
    props.put("bootstrap.servers", bootstrapServers)
    props.put("key.serializer", classOf[StringSerializer].getName)
    props.put("value.serializer", classOf[StringSerializer].getName)
    props.put("acks", "all") // Ensure data durability
    props.put("retries", 3) // Retry failed sends
    props.put("batch.size", 16384) // Batch size for better throughput
    props.put("linger.ms", 5) // Wait up to 5ms to batch records
    props.put("buffer.memory", 33554432) // 32MB buffer
    props.put("compression.type", "snappy") // Compress data
    props.put("max.in.flight.requests.per.connection", 5)
    props.put("enable.idempotence", true) // Ensure exactly-once semantics
    
    new KafkaProducer[String, String](props)
  }
  
  /**
   * Send sensor data to Kafka topic
   * @param sensorData The sensor data to send
   * @return Future containing the result
   */
  def sendSensorData(sensorData: SensorData): ScalaFuture[RecordMetadata] = {
    val promise = Promise[RecordMetadata]()
    
    try {
      val jsonData = objectMapper.writeValueAsString(sensorData)
      val key = s"${sensorData.vehicleId}_${sensorData.sensorId}"
      
      val record = new ProducerRecord[String, String](topicName, key, jsonData)
      
      val callback = new Callback {
        override def onCompletion(metadata: RecordMetadata, exception: Exception): Unit = {
          if (exception != null) {
            promise.failure(exception)
          } else {
            promise.success(metadata)
          }
        }
      }
      
      producer.send(record, callback)
      
    } catch {
      case e: Exception => promise.failure(e)
    }
    
    promise.future
  }
  
  /**
   * Send batch of sensor data
   * @param sensorDataList List of sensor data records
   * @return Future containing list of results
   */
  def sendBatch(sensorDataList: List[SensorData]): ScalaFuture[List[RecordMetadata]] = {
    val futures = sensorDataList.map(sendSensorData)
    ScalaFuture.sequence(futures)
  }
  
  /**
   * Flush any pending records
   */
  def flush(): Unit = {
    producer.flush()
  }
  
  /**
   * Close the producer
   */
  def close(): Unit = {
    producer.close()
  }
}

/**
 * Sensor Data Case Class
 * Represents automotive sensor data structure
 */
case class SensorData(
  timestamp: String,
  sensorId: String,
  vehicleId: String,
  sensorType: String,
  location: Location,
  measurements: Map[String, Any],
  metadata: Map[String, Any]
)

case class Location(
  latitude: Double,
  longitude: Double
)

/**
 * Producer Factory for creating configured producers
 */
object SensorDataProducer {
  
  def apply(bootstrapServers: String, topicName: String): SensorDataProducer = {
    new SensorDataProducer(bootstrapServers, topicName)
  }
  
  /**
   * Create producer with default configuration
   */
  def createDefault(): SensorDataProducer = {
    val bootstrapServers = sys.env.getOrElse("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    val topicName = sys.env.getOrElse("KAFKA_TOPIC", "sensor-data")
    new SensorDataProducer(bootstrapServers, topicName)
  }
}

/**
 * Main application for testing the producer
 */
object SensorDataProducerApp extends App {
  
  val producer = SensorDataProducer.createDefault()
  
  try {
    // Generate sample sensor data
    val sampleData = List(
      SensorData(
        timestamp = java.time.Instant.now().toString,
        sensorId = "radar_001",
        vehicleId = "VH_12345",
        sensorType = "radar",
        location = Location(47.4979, 19.0402),
        measurements = Map(
          "distance" -> 150.5,
          "speed" -> 65.2,
          "angle" -> 12.3,
          "confidence" -> 0.95
        ),
        metadata = Map(
          "firmware_version" -> "2.1.3",
          "calibration_date" -> "2024-01-01"
        )
      )
    )
    
    // Send data
    val result = producer.sendBatch(sampleData)
    
    result.onComplete {
      case Success(metadataList) =>
        println(s"Successfully sent ${metadataList.length} records")
        metadataList.foreach { metadata =>
          println(s"Record sent to partition ${metadata.partition()}, offset ${metadata.offset()}")
        }
      case Failure(exception) =>
        println(s"Failed to send data: ${exception.getMessage}")
    }
    
    // Wait for completion
    Thread.sleep(5000)
    
  } finally {
    producer.close()
  }
}
