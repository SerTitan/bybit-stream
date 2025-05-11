import json
from confluent_kafka.admin import AdminClient, NewTopic
from pyflink.common import Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource, KafkaSink, KafkaRecordSerializationSchema, KafkaOffsetsInitializer
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy

KAFKA_BOOTSTRAP = "kafka:9092"
INPUT_TOPIC = "bybit_trades"
OUTPUT_TOPIC = "bybit_avg"


def ensure_topic_exists(topic_name):
    admin = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP})
    topics = admin.list_topics(timeout=10).topics
    if topic_name not in topics:
        print(f"[INFO] Topic '{topic_name}' not found. Creating...")
        admin.create_topics([NewTopic(topic_name, num_partitions=1, replication_factor=1)])
    else:
        print(f"[INFO] Topic '{topic_name}' exists.")


def parse_trade(raw: str):
    """Парсит сообщение, возвращает (symbol, price) или None."""
    try:
        t = json.loads(raw)["data"][0]
        return t["s"], float(t["p"])
    except Exception:
        return None


if __name__ == "__main__":
    ensure_topic_exists(INPUT_TOPIC)

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    source = KafkaSource.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP) \
        .set_topics(INPUT_TOPIC) \
        .set_group_id("flink-group") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()

    sink = KafkaSink.builder() \
        .set_bootstrap_servers(KAFKA_BOOTSTRAP) \
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(OUTPUT_TOPIC)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        ) \
        .build()

    env.from_source(source, WatermarkStrategy.no_watermarks(), "Kafka Source") \
        .map(parse_trade, output_type=Types.TUPLE([Types.STRING(), Types.FLOAT()])) \
        .filter(lambda x: x is not None) \
        .key_by(lambda x: x[0]) \
        .reduce(lambda a, b: (a[0], (a[1] + b[1]) / 2)) \
        .map(lambda x: f"{x[0]} avg: {x[1]:.2f}", output_type=Types.STRING()) \
        .sink_to(sink)

    env.execute("Flink Kafka Average Price")
