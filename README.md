# Static Website Template

Tool for building templated website layouts into a static website using Python.

* [Static Website Template](#static-website-template)
    * [First Time Setup](#first-time-setup)
    * [Using the Tools](#using-the-tools)

---

## First Time Setup

> [!IMPORTANT]
> These steps should be done *in order*.

* [ ] Update the [license](./LICENSE.txt) with your identifier.
* [ ] Update the [configuration](./config.toml).
* [ ] Review the content of the primary [page template](./templates/page.html) and modify as required.
* [ ] Review the content of the template [index page](./content/index.html) and modify as required.
* [ ] Update the [favicons](./content/images/favicon/) using [RealFaviconGenerator](https://realfavicongenerator.net) with the `Favicon path` set to `images/favicon/`.
* [ ] Update the [site.webmanifest](./content/images/favicon/site.webmanifest).
* [ ] Update the [social media banner](./content/images/banner.png).
* [ ] Add any legal attributions that are required in the [content directory](./content/legal/) and the [config](./config.toml).
* [ ] Build the static website [as specified](#using-the-tools) for the first time.
* [ ] (Optional) Remove this section and update README.

## Using the Tools

These steps assume you are using the [uv](https://docs.astral.sh/uv/) package manager.

1. Create a Python environment at the root of this project: `uv venv`
1. View the available commands by running: `uv run main.py -h`
