from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any

from monosi.drivers.column import ColumnDataType
from monosi.monitors.base import Monitor, MonitorType

@dataclass
class TableMetricsMonitor(Monitor):
    TYPE = MonitorType.TableMetrics

    table: str = field(default_factory=str)
    timestamp_field: str = field(default_factory=str)
    columns: Optional[List[str]] = field(default_factory=list)
    metrics: Optional[List[str]] = field(default_factory=list)
    where: str = field(default_factory=str)

    def info(self):
        return "{}: {}".format(self.table, self.TYPE.value)

    @classmethod # TODO: Implement validation
    def validate(cls, monitor_dict):
        pass

    def _columns_to_metrics(self, columns):
        def _remove_special_keys(column):
            return column.name.lower() not in MetricCompiler.SPECIAL_KEYS

        return [Metric.parse_alias(column.name) for column in filter(_remove_special_keys, columns)]

    def _execute_sql(self, config):
        from monosi.drivers.factory import load_driver
        driver_config = config.config
        driver_cls = load_driver(driver_config)

        driver = driver_cls(driver_config)
        compiler_cls = driver_cls.get_compiler()
        compiler = compiler_cls()

        columns = driver.describe_table(self.table)
        compiled_sql = compiler.build_query(self, columns)

        results = driver.execute_sql(compiled_sql)
        metrics = compiler.interpret_results(results)

        return metrics

    def execute(self, config):
        metrics = self._execute_sql(config)

        return metrics

class MetricType(Enum):
    COMPLETENESS = 'completeness'
    APPROX_DISTINCT_COUNT = 'approx_distinct_count'
    APPROX_DISTINCTNESS = 'approx_distinctness'
    MEAN_LENGTH = 'mean_length'
    MAX_LENGTH = 'max_length'
    MIN_LENGTH = 'min_length'
    STD_LENGTH = 'std_length'
    TEXT_INT_RATE = 'text_int_rate'
    TEXT_NUMBER_RATE = 'text_number_rate'
    TEXT_UUID_RATE = 'text_uuid_rate'
    TEXT_ALL_SPACES_RATE = 'text_all_spaces_rate'
    TEXT_NULL_KEYWORD_RATE = 'text_null_keyword_rate'
    ZERO_RATE = 'zero_rate'
    NEGATIVE_RATE = 'negative_rate'
    NUMERIC_MEAN = 'numeric_mean'
    NUMERIC_MIN = 'numeric_min'
    NUMERIC_MAX = 'numeric_max'
    NUMERIC_STD = 'numeric_std'

    @classmethod
    def default_for(cls, column_data_type: ColumnDataType):
        if column_data_type == ColumnDataType.STRING:
            return cls._string_types()
        elif column_data_type == ColumnDataType.INTEGER:
            return cls._number_types()
        
        return []

    @classmethod
    def _string_types(cls):
        return [
            cls.COMPLETENESS,
            cls.APPROX_DISTINCT_COUNT,
            cls.APPROX_DISTINCTNESS,
            cls.MEAN_LENGTH,
            cls.MAX_LENGTH,
            cls.MIN_LENGTH,
            cls.STD_LENGTH,
            cls.TEXT_INT_RATE,
            cls.TEXT_NUMBER_RATE,
            cls.TEXT_UUID_RATE,
            cls.TEXT_ALL_SPACES_RATE,
            cls.TEXT_NULL_KEYWORD_RATE,
        ]
    
    @classmethod
    def _number_types(cls):
        return [
            cls.COMPLETENESS,
            cls.ZERO_RATE,
            cls.NEGATIVE_RATE,
            cls.APPROX_DISTINCTNESS,
            cls.NUMERIC_MEAN,
            cls.NUMERIC_MIN,
            cls.NUMERIC_MAX,
            cls.NUMERIC_STD,
        ]

    @classmethod
    def all(cls):
        return cls.__members__.values()

@dataclass
class MetricDataPoint:
    value: float
    window_start: str
    window_end: str

# TODO: Type Check
# TODO: Driver should override metric implementation, not resoultion of metric
@dataclass
class Metric:
    table_name: str
    column_name: str
    metric_type: MetricType
    values: List[Any]

    METRIC_COLUMN = "{sql} AS {alias}"

    def sql(self):
        unformatted_sql = self.__class__._retrieve_unformatted_sql(self.metric_type)
        formatted_sql = unformatted_sql.format(self.column_name)

        metric_sql = self.__class__.METRIC_COLUMN.format(
            sql=formatted_sql,
            alias=self.alias
        )
        return metric_sql

    @classmethod
    def parse_alias(cls, alias: str):
        # TODO: This assumes no previous "__", which we can't
        parts = alias.lower().split("__")
        
        if len(parts) != 2:
            raise Exception("Could not parse metric alias")

        column_name = parts[0].lower()
        metric_name = parts[1].lower()
        
        return (column_name, metric_name)

    def nonnull_values(self):
        for point in self.values:
            try:
                point.value = float(point.value)
            except Exception:
                pass

        return list(filter(lambda x: x.value != None, self.values))

    @property
    def alias(self):
        return "{}__{}".format(self.column_name, self.metric_type.value)

    @classmethod
    def _retrieve_unformatted_sql(cls, metric_type: MetricType) -> str:
        if metric_type == MetricType.COMPLETENESS:
            return cls.completeness()
        elif metric_type == MetricType.APPROX_DISTINCT_COUNT:
            return cls.approx_distinct_count()
        elif metric_type == MetricType.APPROX_DISTINCTNESS:
            return cls.approx_distinctness()
        elif metric_type == MetricType.MEAN_LENGTH:
            return cls.mean_length()
        elif metric_type == MetricType.MAX_LENGTH:
            return cls.max_length()
        elif metric_type == MetricType.MIN_LENGTH:
            return cls.min_length()
        elif metric_type == MetricType.STD_LENGTH:
            return cls.std_length()
        elif metric_type == MetricType.TEXT_INT_RATE:
            return cls.text_int_rate()
        elif metric_type == MetricType.TEXT_NUMBER_RATE:
            return cls.text_number_rate()
        elif metric_type == MetricType.TEXT_UUID_RATE:
            return cls.text_uuid_rate()
        elif metric_type == MetricType.TEXT_ALL_SPACES_RATE:
            return cls.text_all_spaces_rate()
        elif metric_type == MetricType.TEXT_NULL_KEYWORD_RATE:
            return cls.text_null_keyword_rate()
        elif metric_type == MetricType.ZERO_RATE:
            return cls.zero_rate()
        elif metric_type == MetricType.NEGATIVE_RATE:
            return cls.negative_rate()
        elif metric_type == MetricType.NUMERIC_MEAN:
            return cls.numeric_mean()
        elif metric_type == MetricType.NUMERIC_MIN:
            return cls.numeric_mean()
        elif metric_type == MetricType.NUMERIC_MAX:
            return cls.numeric_max()
        elif metric_type == MetricType.NUMERIC_STD:
            return cls.numeric_std()
        else:
            raise Exception("Unreachable: Metric type is defined that does not resolve to a definition.")

    @classmethod
    def completeness(cls):
        return "COUNT({}) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def approx_distinct_count(cls):
        return "COUNT(DISTINCT {})"

    @classmethod
    def approx_distinctness(cls):
        return "COUNT(DISTINCT {}) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def mean_length(cls):
        return "AVG(LENGTH({}))"

    @classmethod
    def max_length(cls):
        return "MAX(LENGTH({}))"

    @classmethod
    def min_length(cls):
        return "MIN(LENGTH({}))"

    @classmethod
    def std_length(cls):
        return "STDDEV(CAST(LENGTH({}) as double))"

    @classmethod
    def text_int_rate(cls):
        return "SUM(IFF(REGEXP_COUNT(TO_VARCHAR({}), '^([-+]?[0-9]+)$', 1, 'i') != 0, 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def text_number_rate(cls):
        return "SUM(IFF(REGEXP_COUNT(TO_VARCHAR({}), '^([-+]?[0-9]*[.]?[0-9]+([eE][-+]?[0-9]+)?)$', 1, 'i') != 0, 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def text_uuid_rate(cls):
        return "SUM(IFF(REGEXP_COUNT(TO_VARCHAR({}), '^([0-9a-fA-F]{{8}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{12}})$', 1, 'i') != 0, 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def text_all_spaces_rate(cls):
        return "SUM(IFF(REGEXP_COUNT(TO_VARCHAR({}), '^(\\\\s+)$', 1, 'i') != 0, 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def text_null_keyword_rate(cls):
        return "SUM(IFF(UPPER({}) IN ('NULL', 'NONE', 'NIL', 'NOTHING'), 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def zero_rate(cls):
        return "SUM(IFF(UPPER({}) IN ('NULL', 'NONE', 'NIL', 'NOTHING'), 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def negative_rate(cls):
        return "SUM(IFF({} < 0, 1, 0)) / CAST(COUNT(*) AS NUMERIC)"

    @classmethod
    def numeric_mean(cls):
        return "AVG({})"

    @classmethod
    def numeric_min(cls):
        return "MIN({})"

    @classmethod
    def numeric_max(cls):
        return "MAX({})"

    @classmethod
    def numeric_std(cls):
        return "STDDEV(CAST({} as double))"

@dataclass
class MetricCompiler:
    metrics: List[Metric] = field(default_factory=list)
    
    SPECIAL_KEYS = ['window_start', 'window_end', 'row_count']

    BASE_SQL = """
    SELECT 
        DATE_TRUNC('HOUR', {timestamp_field}) as window_start, 
        DATEADD(hr, 1, DATE_TRUNC('HOUR', {timestamp_field})) as window_end, 

        COUNT(*) as row_count, 

        {metric_sql}

    FROM {table}
    WHERE 
        DATE_TRUNC('HOUR', {timestamp_field}) >= DATEADD(day, {days_ago}, CURRENT_TIMESTAMP()) 
    GROUP BY window_start, window_end 
    ORDER BY window_start ASC;
    """

    @classmethod
    def _create_metrics(cls, table_name, columns):
        metrics = []

        for column in columns:
            column_name = column.name
            column_data_type = column.data_type

            for metric_type in MetricType.default_for(column_data_type):
                metric = Metric(
                    table_name=table_name,
                    column_name=column_name, 
                    metric_type=metric_type,
                    values=[],
                )
                metrics.append(metric)

        return metrics

    def build_query(self, monitor, columns):
        self.metrics = MetricCompiler._create_metrics(monitor.table, columns)
        metric_sql = ",\n".join([metric.sql() for metric in self.metrics])

        # TODO: Set to reasonable default
        days_ago = -85788

        query = MetricCompiler.BASE_SQL.format(
            metric_sql=metric_sql,
            timestamp_field=monitor.timestamp_field,
            table=monitor.table,
            days_ago=days_ago,
        )
        return query

    def _metric_map(self):
        metric_map = {}

        for metric in self.metrics:
            column_name = metric.column_name.lower()
            metric_name = metric.metric_type._value_.lower()

            if column_name not in metric_map:
                metric_map[column_name] = {}
            
            metric_map[column_name][metric_name] = metric
        
        return metric_map

    def interpret_results(self, results) -> List[Metric]:
        metric_map = self._metric_map()

        pivot = {}
        for row in results['rows']:
            window_start = row['WINDOW_START']
            window_end = row['WINDOW_END']
            row_count = row['ROW_COUNT']
            
            for alias in row.keys():
                if "__" not in alias: # TODO: Not durable
                    continue

                column_name, metric_name = Metric.parse_alias(alias)
                metric = metric_map[column_name][metric_name]

                # TODO: Issue here! Can't assume float.
                try:
                    value = float(row[alias])
                except TypeError:
                    value = None

                data_point = MetricDataPoint(
                    window_start=window_start,
                    window_end=window_end,
                    value=value,
                )
                metric.values.append(data_point)

        metrics = []
        for column in metric_map.keys():
            for metric in metric_map[column]:
                metrics.append(metric_map[column][metric])

        return metrics

