В корне проекта исполняем:
* docker-compose build
* docker-compose up -d 

После этого все контейнеры поднимутся, порты для доступа UI можно посмотреть в docker-compose.yml. Для демонстрации работы таски для флинка необходимо исполнить команду:
* docker exec -it bybit-stream-jobmanager-1 flink run -d -py /opt/flink/usrlib/flink_average_price.py

После этого можно открыть веб api по адресу http://localhost:8000/static/api.html и увидеть как все работает!

Для доступа к таблице с данными в БД:
* docker exec -it bybit-stream-postgres-1 psql -U bybit -d bybitdb
* COPY (
    SELECT symbol, price, timestamp FROM trades
    WHERE timestamp >= '2025-05-12 23:19:00'
    AND timestamp < '2025-05-12 23:20:00'
    ORDER BY timestamp
) TO '/var/lib/postgresql/data/trades_export.csv' DELIMITER ',' CSV HEADER;
* docker cp bybit-stream-postgres-1:/var/lib/postgresql/data/trades_export.csv ./trades_export.csv

Если указать нужный временной промежуток, можно будет подтвердить одинаковое количество записей в веб-интерфейсе и в БД.
