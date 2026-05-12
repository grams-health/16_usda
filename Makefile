SERVICE := usda

.PHONY: unit-test pact-verify

unit-test:
	docker build --target test -t $(SERVICE)-test .
	docker run --rm $(SERVICE)-test

pact-verify:
	docker build --target contract -t $(SERVICE)-contract .
	docker run --rm --network host \
		-e PACT_BROKER_URL=$${PACT_BROKER_URL:-http://localhost:9292} \
		$(SERVICE)-contract
