# Iteration 3 - Bonus Features and Delivery

The final iteration added Redis-backed live messages and notifications,
RabbitMQ/Celery scheduled delivery, reconnect handling, pending-message
management, Docker/Nginx integration, demo data, and the formal traceability
report. The plan was met. The scheduling design was improved from a single
long-lived ETA task to a database-backed due-message scan so pending messages
survive worker or broker restarts and repeated task execution cannot duplicate
delivery.

Every member reviewed the area connected to their presentation role, while QA
ran backend, frontend, security, build, and packaging checks. The team was
satisfied with the final result: all mandatory and both bonus requirements are
part of one coherent product, the interface remains faithful to the Phase 1
wireframes, and setup is reproducible from the repository.

