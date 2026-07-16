.PHONY: bootstrap dev-web dev-api dev-vercel build-vercel smoke-vercel-local smoke-preview run-example benchmark-simulation benchmark-repeated benchmark-comparison lint typecheck test build verify

bootstrap:
	pnpm bootstrap

dev-web:
	pnpm dev:web

dev-api:
	pnpm dev:api

dev-vercel:
	pnpm dev:vercel

build-vercel:
	pnpm build:vercel

smoke-vercel-local:
	pnpm smoke:vercel-local

smoke-preview:
	pnpm smoke:preview

run-example:
	pnpm run-example

benchmark-simulation:
	pnpm benchmark:simulation

benchmark-repeated:
	pnpm benchmark:repeated

benchmark-comparison:
	pnpm benchmark:comparison

lint:
	pnpm lint

typecheck:
	pnpm typecheck

test:
	pnpm test

build:
	pnpm build

verify:
	pnpm verify
