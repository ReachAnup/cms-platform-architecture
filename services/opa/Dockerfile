# syntax=docker/dockerfile:1
# Local OPA service image
FROM openpolicyagent/opa:latest

# Copy OPA configuration
COPY config.yaml /config.yaml

# Default run can be overridden by docker-compose command
CMD ["run", "--server", "--addr", ":8181", "--diagnostic-addr", ":8282", "--config-file", "/config.yaml"]
