# Developer Documentation

The template I've used has linting/code style fixing built in. Check out `Makefile`;
`make fix-py` will run the `ruff` code formatter over your code.
Run it before committing and fix/flag as ignored anything it can't fix itself.

## Introduction

This uses Iommi, a very powerful and flexible framework for building websites in Python.
[The documentation is here](https://docs.iommi.rocks/), but it can be a bit hard to get your head around.
[The cookbook pages](https://docs.iommi.rocks/cookbook.html) are a good thing to refer to.

Examples are good as well, so I'll just outline a few key concepts to understand the code:

### Two Ways of Doing Anything

There's basically two ways of doing anything - **procedural** and **declarative**.
Example - building a form to edit a specific instance of a model, **procedurally**:

```python
view = Form(
    auto__model=MyDjangoModel,
    instance=lambda params, **_: params.my_django_model
)
```

and **declaratively**, where the `class Meta` is basically just what you'd give as arguments:

```python
class MyForm(Form):
    class Meta:
        auto__model=MyDjangoModel
        instance=lambda params, **_: params.my_django_model
        
view = MyForm()
```

In this example, the stuff in `app.main_menu.py` is mostly **procedural**,
and there's an example of a more complicated view in `app.pages.py` (that gets included into `main_menu`).

### Refinables

Everything is built out of 'refinables'. For example, `Form` has some settings for automatically generating it from a model.
Example - Building a form to edit *only* the name and height of \`MyDjangoModel:

```python
Form(
    auto=dict{
        model=MyDjangoModel
        include=['name', 'height']
    }
)
```

But you can also skip providing the dict of options with just double underscores:

```python
Form(
    auto__model=MyDjangoModel,
    auto__include=['name', 'height']
)
```

Anything not specified will have its default value.

### Function Arguments

A lot of arguments can be provided as functions that evaluate at runtime.
Example - Building a form that's only editable if you're staff:

```python
Form(
    editable=lambda user, **_: user.is_staff
)
```

```python
class MyForm(Form):
    class Meta:
        editable=lambda user, **_: user.is_staff
```

If you need the functions to be more complicated, then in the **procedural** frame you can declare them elsewhere.
Example - Making a form editable only by Steve. Needs to make sure the user is signed in, so they *have* a name to check.

```python
def staff_and_steve(user) -> bool:
    if not user.is_authenticated:
        return False
    else if user.is_staff and user.first_name == 'Steve':
        return True 
    return False

view = Form(
    editable=lambda user, **_: staff_and_steve(user)
)
```

Or declaratively:

```python
class MyForm(Form):
    class Meta:
        @staticmethod
        def editable(user, **_) -> bool:
            if not user.is_authenticated:
                return False
            else if user.is_staff and user.first_name == 'Steve':
                return True 
            return False

view = MyForm()
```

### Function Argument Parameters

The functions are passed a set of parameters. The values available vary, but it's generally `request`,
`params` (which contains any view parameters), `user` (a shortcut to `request.user`) and any you've specified using
**path decoding** (where you register a model, and then paths containing it put it in the context).
See `app.apps.AppConfig` and `app.main_menu -> cats.items.detail`.

## Rules

The app has object-level permissions, applied using [django-rules](https://github.com/dfunckt/django-rules).
These are defined for each model in the model files, after the model itself.

They fit pretty well into Iommi's structure, so it's easy to check when setting up a URL or whatever
if you're allowed to view/edit/whatever the object.

## Local Testing Setup & Quickstart

For a new developer setting up the platform locally for debugging and development:

1. **System Dependencies & Environment**:
   Install Miniforge or Miniconda, and create the conda environment with the required astronomical packages:
   ```bash
   conda create -y -n astro python=3.14 astropy pymc pytensor thejoker numpy scipy matplotlib -c conda-forge
   conda activate astro
   ```

2. **Repository Setup**:
   Clone the repository and copy the default environment file:
   ```bash
   git clone git@github.com:Gaia-COB/gaia-cob-pmp.git
   cd gaia-cob-pmp
   cp .env.default .env
   ```
   Set `DEBUG=True` and `SOCIALACCOUNT_ONLY=false` in `.env` to enable local email/password authentication.

3. **Database Initialization**:
   Apply migrations and load the pre-computed Keplerian fits and database fixtures:
   ```bash
   python gaia_cob_pmp/manage.py migrate
   python gaia_cob_pmp/manage.py loaddata gaia_cob_pmp/app/fixtures/*.json
   ```

4. **Create a Local Test Superuser**:
   Run the following python script via Django's shell to register a local administrator:
   ```bash
   python gaia_cob_pmp/manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='testuser').exists() or User.objects.create_superuser('testuser', 'test@example.com', 'password123')"
   ```

5. **Run Automated Tests**:
   To run tests and verify the rejection sampler:
   ```bash
   PYTHONPATH=gaia_cob_pmp python gaia_cob_pmp/manage.py test tests
   ```

6. **Start Local Development Server**:
   Start the server and visit `http://localhost:8000/accounts/login/` (log in with `testuser` / `password123`):
   ```bash
   PYTHONPATH=gaia_cob_pmp python gaia_cob_pmp/manage.py runserver
   ```

