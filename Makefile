## H. Haruna Portfolio — Hugo + Blowfish (Agentic static build)
## `make help` for the target list. Uses host-installed tools (no vendored binaries).

# -- Toolchain & theme ---------------------------------------------------------
# Host requirements: hugo (extended, supported by Blowfish: 0.164-0.167;
# newer builds print an advisory warning), go, taplo (`brew install taplo`),
# node+markdownlint-eslint via npx.
HUGO     ?= hugo
TAPLO    ?= taplo
THEME    := github.com/nunocoracao/blowfish/v3
BASE_URL ?= http://localhost:1313/
PORT     ?= 1313

.PHONY: help setup tidy update dev build build-strict check lint media-check media-optimize i18n-check images-audit clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## First-run: fetch the Blowfish theme via Hugo modules
	$(HUGO) mod get $(THEME)
	$(HUGO) mod tidy
	@echo "✔ Theme installed. Run 'make dev'."

tidy: ## Reconcile go.mod/go.sum with module imports
	$(HUGO) mod tidy

update: ## Update Blowfish to the latest upstream release
	$(HUGO) mod get -u $(THEME)

dev: ## Live-reload dev server (http://localhost:$(PORT))
	$(HUGO) server -p $(PORT) --buildDrafts --baseURL $(BASE_URL)

lint: ## Enforced quality gate: markdownlint + ESLint (JS) + taplo (TOML lint+format)
	@npx --yes markdownlint-cli2 "**/*.md" "!public/**" "!node_modules/**" "!.tools/**"
	@npx --yes eslint --no-error-on-unmatched-pattern .
	@$(TAPLO) lint "config/_default/*.toml"
	@$(TAPLO) format --check "config/_default/*.toml"

check: lint media-check i18n-check build-strict ## Gate: lint + media + translations + strict build (CI entry point)

build: ## Production build into ./public
	$(HUGO) --gc --minify --baseURL $(BASE_URL)

build-strict: ## Strict build: path + template warnings surfaced
	$(HUGO) --gc --minify --printPathWarnings --templateMetricsHints --baseURL $(BASE_URL)
	@test -s public/index.html && echo "✔ build OK"

media-check: ## Fail when content/templates reference external media (no hotlinking, self-hosted only)
	@hits=$$(grep -rnE \
	  "static\.wixstatic|video\.wixstatic|youtube\.com/embed|https?://[^\"' ).]+\.(jpe?g|png|avif|webp|gif|svg|mp4|webm)" \
	  content layouts --include='*.md' --include='*.html' 2>/dev/null | grep -v "^\s*<!--" || true); \
	if [ -n "$$hits" ]; then \
	  echo "external media references found (must be self-hosted):"; \
	  printf '%s\n' "$$hits"; exit 1; \
	fi; \
	echo "✔ media: all served from this site"

i18n-check: ## Fail when a source-of-truth EN content page lacks a .ja.md translation
	@miss=$$(for f in $$(find content -name '*.md' ! -name '*.ja.md' | sort); do \
	  base=$${f%.md}; \
	  [ -f "$$base.ja.md" ] || echo "missing JA translation: $$f"; \
	done); \
	if [ -n "$$miss" ]; then \
	  printf '%s\n' "$$miss"; exit 1; \
	fi; \
	echo "✔ i18n: every EN page has a Japanese translation"

images-audit: ## List images >2MB (candidates for recompression)
	@find content assets -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -size +2M -print

media-optimize: ## Optimize PNG/JPEG under content/ + assets/ in-place (pngquant + jpegoptim); untouched copies kept in originals/ (gitignored safety net)
	@before=$$(du -sk content assets 2>/dev/null | cut -f1 | paste -sd+ | bc); \
	find content assets -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -print0 | \
	  xargs -0 -r -I{} sh -c 'test -e originals/{} || { mkdir -p originals/$$(dirname {}); cp {} originals/{}; }'; \
	find content assets -type f -iname '*.png' -print0 | xargs -0 -r pngquant --strip --skip-if-larger --quality 70-95 --force --ext .png; \
	find content assets -type f \( -iname '*.jpg' -o -iname '*.jpeg' \) -print0 | xargs -0 -r jpegoptim --strip-all --max=85 --quiet; \
	after=$$(du -sk content assets 2>/dev/null | cut -f1 | paste -sd+ | bc); \
	echo "✔ media-optimize done ($$before KB -> $$after KB; originals preserved in .gitignored originals/)"

clean: ## Remove build artifacts
	rm -rf public resources/_gen .hugo_build.lock
