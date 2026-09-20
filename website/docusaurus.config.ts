import type {Config} from '@docusaurus/types';
const config: Config = {
  "title": "ignition-mcp",
  "tagline": "A local HTTP front for `ign mcp serve`: every ign tool, plus composite workflows, resources, and prompts.",
  "favicon": "img/favicon.svg",
  "url": "https://whiskeyhouse.github.io",
  "baseUrl": "/ignition-mcp/",
  "trailingSlash": true,
  "organizationName": "WhiskeyHouse",
  "projectName": "ignition-mcp",
  "onBrokenLinks": "throw",
  "markdown": {
    "format": "md",
    "hooks": {
      "onBrokenMarkdownLinks": "throw"
    }
  },
  "presets": [
    [
      "classic",
      {
        "docs": {
          "path": "../docs",
          "sidebarPath": "./sidebars.ts",
          "editUrl": "https://github.com/WhiskeyHouse/ignition-mcp/edit/main/docs/",
          "exclude": [
            "superpowers/**",
            "*_SUMMARY.md",
            "*_REPORT.md",
            "*-STRATEGY.md",
            "*_COMPLETE.md",
            "AI_DEVELOPMENT_RULES.md",
            "BINDING_PATTERNS_ANALYSIS.md",
            "GETTING_STARTED.md",
            "LINTER_USAGE.md",
            "SUPPRESSION.md",
            "PROJECT_OVERVIEW.md",
            "IGNITION-LINTER-INTEGRATION.md"
          ]
        },
        "blog": false,
        "theme": {
          "customCss": "./src/css/custom.css"
        }
      }
    ]
  ],
  "themeConfig": {
    "colorMode": {
      "defaultMode": "dark",
      "respectPrefersColorScheme": true
    },
    "navbar": {
      "title": "ignition-mcp",
      "items": [
        {
          "to": "/docs/installation",
          "label": "Get started",
          "position": "left"
        },
        {
          "type": "docSidebar",
          "sidebarId": "docsSidebar",
          "label": "Docs",
          "position": "left"
        },
        {
          "label": "Tools",
          "type": "dropdown",
          "items": [
            {
              "label": "Ignition Dev Tools",
              "href": "https://thethoughtagen.github.io/ignition-ide-plugins/"
            },
            {
              "label": "ignition-lint",
              "href": "https://thethoughtagen.github.io/ignition-lint/"
            },
            {
              "label": "ignition-cli",
              "href": "https://thethoughtagen.github.io/ignition-cli/"
            },
            {
              "label": "Ignition Git Module",
              "href": "https://whiskeyhouse.github.io/ignition-git-module/"
            }
          ],
          "position": "left"
        },
        {
          "href": "https://github.com/WhiskeyHouse/ignition-mcp/releases",
          "label": "Releases",
          "position": "right"
        },
        {
          "href": "https://github.com/WhiskeyHouse/ignition-mcp",
          "label": "GitHub",
          "position": "right"
        }
      ]
    },
    "footer": {
      "style": "dark",
      "links": [
        {
          "title": "Documentation",
          "items": [
            {
              "label": "Installation",
              "to": "/docs/installation"
            },
            {
              "label": "First steps",
              "to": "/docs/quickstart"
            },
            {
              "label": "Report an issue",
              "href": "https://github.com/WhiskeyHouse/ignition-mcp/issues"
            }
          ]
        },
        {
          "title": "Related tools",
          "items": [
            {
              "label": "Ignition Dev Tools",
              "href": "https://thethoughtagen.github.io/ignition-ide-plugins/"
            },
            {
              "label": "ignition-lint",
              "href": "https://thethoughtagen.github.io/ignition-lint/"
            },
            {
              "label": "ignition-cli",
              "href": "https://thethoughtagen.github.io/ignition-cli/"
            },
            {
              "label": "Ignition Git Module",
              "href": "https://whiskeyhouse.github.io/ignition-git-module/"
            }
          ]
        },
        {
          "title": "Patrick Mannion",
          "items": [
            {
              "label": "FIELDNOTES",
              "href": "https://awake-iris-z6ww.here.now/"
            },
            {
              "label": "LinkedIn",
              "href": "https://www.linkedin.com/in/mannionpatrick/"
            },
            {
              "label": "X",
              "href": "https://x.com/__pattym__"
            }
          ]
        }
      ],
      "copyright": "Community tooling for Ignition. See each repository for its license and contributors."
    }
  }
};
export default config;
