# NIO API Development Patterns

## Controller Structure (BaseApi)

Every API endpoint in `nio-api3` is a controller class inheriting from `BaseApi`:

```python
from nioapi.api.lib.base_api import BaseApi
from nioapi.api.lib.base_api import base_api_decorator
from nioapi.api.lib.base_api import get_response_codes
from nioapi.api.lib.swagger import swagger_table
from nioapi.api.lib.codes import NioResponse
from nioapi.api.lib.postgres_config import get_analytics_pg_helper
from nioapi.api.lib.exceptions import BadRequestException

pg_helper = get_analytics_pg_helper()

class MyController(BaseApi):
    component_id = "analytics.api.my_feature"

    @base_api_decorator(
        description=swagger_table(["DB_PG"]),
        parameters=[
            NioParam("my_id").dataType("int").description("...").paramType("path").required(),
            NioParam("body_data").paramType("body").dataType("json"),
        ],
        responses=get_response_codes(
            extra=[NioResponse(452, "Invalid response")],
        ),
    )
    def get(self, my_id):
        try:
            args = self.get_args()
            # ... build SQL, query, return
            data = pg_helper.sql_query(sql, values)
            return self.handle_response_json({"data": data})
        except Exception as ex:
            return self.handle_exception(ex)

    def post(self):
        try:
            body = self.get_body()
            data = body["data"]
            new_id = pg_helper.sql_insert_map(
                table="my_table",
                mapping={"col1": data["col1"]},
                return_id="id"
            )
            return self.handle_response_json({"data": {"id": new_id}})
        except Exception as ex:
            return self.handle_exception(ex)
```

## PgHelper Database Operations

```python
from nioapi.api.lib.postgres_config import get_analytics_pg_helper
pg_helper = get_analytics_pg_helper()

# Query
rows = pg_helper.sql_query("SELECT * FROM t WHERE id = %s", [my_id])

# Insert
new_id = pg_helper.sql_insert_map(
    table="my_table",
    mapping={"col1": val1, "col2": val2},
    return_id="id"
)

# Update / Delete
pg_helper.sql_execute("UPDATE t SET col = %s WHERE id = %s", [val, id])

# Where clause builder
where_clauses_list = [
    {"clause": "col = %(col)s", "key": "col", "value": val},
]
values, where_clauses = pg_helper.get_values_and_where_clauses({}, where_clauses_list)
```

## Route Registration

Add routes in `nio-api3/src/nioapi/api/routes.py`:

```python
api_routes = [
    {
        "class": MyController,
        "endpoint": "/v0/my_feature/<int:my_id>",
        "group": groups.my_group,
        "role": roles.mrs,
        "wrap": True,
    },
]
```

Key fields:
- `class`: Controller class
- `endpoint`: URL pattern (Flask-style)
- `group`: Feature group (used for configuration/feature flags)
- `role`: Deployment role (e.g., `mrs`, `ncore`)
- `wrap`: `True` for standard request wrapping


External routes go in `routes_external.py`.

## Request Body Handling

For nested JSON request bodies:

```python
# In parameter list:
NioParam("my_filter").paramType("body").dataType("json")

# In method:
body = self.get_body()
filters = body["my_filter"]
```

## Response Methods

| Method | Use Case |
|---|---|
| `handle_response_json(data, code=200)` | Standard JSON response |
| `handle_response_html(html, code=200)` | HTML response |
| `handle_response_stream(response)` | Streaming response |
| `handle_response_file(filepath, filename, mimetype)` | File download |
| `handle_exception(ex)` | Error handling (always use in except blocks) |

## XDR Column Configuration

### PCCT Config (`pcct_config.py`)

Defines procedure/cause/cause-type relationships per interface:

```python
COLUMNS_PCCT = {
    "N1/N2": {
        "ngap_proc_id": {
            "count": 2,
            "key_type": KEY_PROC,
            "array_key": "ngap_proc_str",
            "cause_pair": "ngap_cause",
        },
        "ngap_cause": {
            "count": 2,
            "key_type": KEY_CAUSE,
            "type": {
                "type_column": "ngap_cause_type",
                "type_mapping": "ngap_cause_type_str_mapping",
            },
            "namespace": "ngap_cause_type_groups",
        },
    },
}
```

### Build Info Mapping (`build_info_mapping.py`)

Maps raw protocol data arrays to internal representations:

```python
CONFIG_PER_PROTOCOL = [
    {
        "file": assets.get_asset_by_id("XDR_NGAP_ARRAYS_FILE"),
        "nio_proc_group_keys": {"n1n2_groups_ngap": "NGAP"},
        "cause_keys": {"ngap_radionetwork_cause_str": ["N1/N2"]},
        "cause_namespaces": "ngap_cause_type_groups",
        "raw_keys": ["ngap_proc_str", "ngap_cause_type_str"],
    },
]
```

### Mapped Columns (`config.py`)

Simple integer-to-string mappings:

```python
COLUMNS_MAPPED = [
    {
        "column": "handover_type",
        "conditions": [{
            "config": {"map_type": "int_mapping", "array_key": "ngap_handover_type_str"},
            "match": {"interface": {"N1/N2"}},
        }],
    },
]
```

## Directory Structure

```
nio-api3/src/nioapi/
├── api/
│   ├── lib/           # BaseApi, PgHelper, exceptions, codes
│   ├── routes.py      # Internal route registration
│   ├── routes_external.py  # External/public routes
│   ├── alerts/        # Alert management endpoints
│   ├── xdr/           # XDR (eXtended Data Record) endpoints
│   ├── trace/         # Packet tracing endpoints
│   ├── rna/           # RNA (Radio Network Analytics)
│   ├── kpi/           # KPI endpoints
│   ├── scv/           # Single Customer View
│   ├── external/      # External-facing endpoints
│   ├── dashboards/    # Dashboard endpoints
│   ├── events/        # Event management
│   ├── feeds/         # Data feed endpoints
│   └── ...            # 40+ domain modules
├── services/          # Background services
├── tools/             # Internal tooling
└── niobench/          # Benchmark utilities
```
