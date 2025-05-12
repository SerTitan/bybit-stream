FROM apache/flink:1.19.0-scala_2.12

# ─── 1) Python + pip + essentials ───────────────────────────────────────────
USER root
RUN apt-get update && apt-get install -y python3 python3-pip curl && apt-get clean

# ─── 2) Python packages for PyFlink + confluent-kafka (admin client) ───────
RUN python3 -m pip install --no-cache-dir apache-flink==1.19.0 protobuf googleapis-common-protos confluent-kafka

# ─── 3) JARs for Flink DataStream + Table API + KafkaSink ──────────────────

# Flink DataStream Kafka connector (KafkaSource)
RUN curl -fsSL \
      https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/1.17.2/flink-connector-kafka-1.17.2.jar \
    -o /opt/flink/lib/flink-connector-kafka-1.17.2.jar

# Flink SQL Kafka connector
RUN curl -fsSL \
      https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/1.17.2/flink-sql-connector-kafka-1.17.2.jar \
    -o /opt/flink/lib/flink-sql-connector-kafka-1.17.2.jar

# Kafka clients (newest compatible version)
RUN curl -fsSL \
      https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar \
    -o /opt/flink/lib/kafka-clients-3.5.1.jar

# Flink shaded guava (mandatory for KafkaSink in 1.19)
RUN curl -fsSL \
      https://repo1.maven.org/maven2/org/apache/flink/flink-shaded-guava/30.1.1-jre-15.0/flink-shaded-guava-30.1.1-jre-15.0.jar \
    -o /opt/flink/lib/flink-shaded-guava-30.1.1-jre-15.0.jar

USER flink
