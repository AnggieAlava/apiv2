from __future__ import annotations
from functools import cache
import re
from typing import Any, Optional
from rest_framework.test import APITestCase
from django.apps import apps
from channels.db import database_sync_to_async
from django.db.models import Model

from breathecode.tests.mixins.generate_models_mixin.utils import create_models, get_list, is_valid, just_one
from breathecode.utils.attr_dict import AttrDict
from . import interfaces
# from django.db.models.query_utils import DeferredAttribute
from django.db.models.fields.related_descriptors import (ReverseManyToOneDescriptor, ManyToManyDescriptor,
                                                         ForwardManyToOneDescriptor)

from ..generate_models_mixin import GenerateModelsMixin
from ..models_mixin import ModelsMixin
from django.db import reset_queries
from django.db import connections
# from django.test.utils import override_settings

__all__ = ['Database']


class Database:
    """Mixin with the purpose of cover all the related with the database"""

    _cache: dict[str, Model] = {}
    _parent: APITestCase
    _bc: interfaces.BreathecodeInterface
    how_many = 0

    def __init__(self, parent, bc: interfaces.BreathecodeInterface) -> None:
        self._parent = parent
        self._bc = bc

    def reset_queries(self):
        reset_queries()

    # @override_settings(DEBUG=True)
    def get_queries(self, db='default'):
        return [query['sql'] for query in connections[db].queries]

    # @override_settings(DEBUG=True)
    def print_queries(self, db='default'):
        print()
        print('---------------- Queries ----------------\n')
        for query in connections[db].queries:
            print(f'{query["time"]} {query["sql"]}\n')

        print('----------------- Count -----------------\n')
        print(f'Queries: {len(connections[db].queries)}\n')
        print('-----------------------------------------\n')

    @classmethod
    def get_model(cls, path: str) -> Model:
        """
        Return the model matching the given app_label and model_name.

        As a shortcut, app_label may be in the form <app_label>.<model_name>.

        model_name is case-insensitive.

        Raise LookupError if no application exists with this label, or no
        model exists with this name in the application. Raise ValueError if
        called with a single argument that doesn't contain exactly one dot.

        Usage:

        ```py
        # class breathecode.admissions.models.Cohort
        Cohort = self.bc.database.get_model('admissions.Cohort')
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        if path in cls._cache:
            return cls._cache[path]

        app_label, model_name = path.split('.')
        cls._cache[path] = apps.get_model(app_label, model_name)

        return cls._cache[path]

    def list_of(self, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
        """
        This is a wrapper for `Model.objects.filter()`, get a list of values of models as `list[dict]` if
        `dict=True` else get a list of `Model` instances.

        Usage:

        ```py
        # get all the Cohort as list of dict
        self.bc.database.get('admissions.Cohort')

        # get all the Cohort as list of instances of model
        self.bc.database.get('admissions.Cohort', dict=False)
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        model = Database.get_model(path)
        result = model.objects.filter()

        if dict:
            result = [ModelsMixin.remove_dinamics_fields(self, data.__dict__.copy()) for data in result]

        return result

    @database_sync_to_async
    def async_list_of(self, path: str, dict: bool = True) -> list[Model | dict[str, Any]]:
        """
        This is a wrapper for `Model.objects.filter()`, get a list of values of models as `list[dict]` if
        `dict=True` else get a list of `Model` instances.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        return self.list_of(path, dict)

    def delete(self, path: str, pk: Optional[int | str] = None) -> tuple[int, dict[str, int]]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).delete()`, delete a element if `pk` is provided else
        all the entries.

        Usage:

        ```py
        # create 19110911 cohorts 🦾
        self.bc.database.create(cohort=19110911)

        # exists 19110911 cohorts 🦾
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 19110911)

        # remove all the cohorts
        self.bc.database.delete(10)

        # exists 19110910 cohorts
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 19110910)
        ```

        # remove all the cohorts
        self.bc.database.delete()

        # exists 0 cohorts
        self.assertEqual(self.bc.database.count('admissions.Cohort'), 0)
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        """

        lookups = {'pk': pk} if pk else {}

        model = Database.get_model(path)
        return model.objects.filter(**lookups).delete()

    def get(self, path: str, pk: int or str, dict: bool = True) -> Model | dict[str, Any]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).first()`, get the values of model as `dict` if
        `dict=True` else get the `Model` instance.

        Usage:

        ```py
        # get the Cohort with the pk 1 as dict
        self.bc.database.get('admissions.Cohort', 1)

        # get the Cohort with the pk 1 as instance of model
        self.bc.database.get('admissions.Cohort', 1, dict=False)
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """
        model = Database.get_model(path)
        result = model.objects.filter(pk=pk).first()

        if dict:
            result = ModelsMixin.remove_dinamics_fields(self, result.__dict__.copy())

        return result

    @database_sync_to_async
    def async_get(self, path: str, pk: int | str, dict: bool = True) -> Model | dict[str, Any]:
        """
        This is a wrapper for `Model.objects.filter(pk=pk).first()`, get the values of model as `dict` if
        `dict=True` else get the `Model` instance.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        - pk(`str | int`): primary key of model.
        - dict(`bool`): if true return dict of values of model else return model instance.
        """

        return self.get(path, pk, dict)

    def count(self, path: str) -> int:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Usage:

        ```py
        self.bc.database.count('admissions.Cohort')
        ```

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """
        model = Database.get_model(path)
        return model.objects.count()

    @database_sync_to_async
    def async_count(self, path: str) -> int:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        return self.count(path)

    @cache
    def _get_models(self) -> list[Model]:
        values = {}
        for key in apps.app_configs:
            values[key] = apps.get_app_config(key).get_models()
        return values

    def camel_case_to_snake_case(self, name):
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

    def _get_model_field_info(self, model, key):
        attr = getattr(model, key)
        meta = vars(attr)['field'].related_model._meta
        model = vars(attr)['field'].related_model
        blank = attr.field.blank
        null = attr.field.null

        result = {
            'field': key,
            'blank': blank,
            'null': null,
            'app_name': meta.app_label,
            'model_name': meta.object_name,
            'handler': attr,
            'model': model,
        }

        if hasattr(attr, 'through'):
            result['custom_through'] = '_' not in attr.through.__name__
            result['through_fields'] = attr.rel.through_fields

        return result

    @cache
    def _get_models_descriptors(self) -> list[Model]:
        values = {}
        apps = self._get_models()

        for app_key in apps:
            values[app_key] = {}
            models = apps[app_key]
            for model in models:
                values[app_key][model.__name__] = {}
                values[app_key][model.__name__]['meta'] = {
                    'app_name': model._meta.app_label,
                    'model_name': model._meta.object_name,
                    'model': model,
                }

                values[app_key][model.__name__]['to_one'] = [
                    self._get_model_field_info(model, x) for x in dir(model)
                    if isinstance(getattr(model, x), ForwardManyToOneDescriptor)
                ]

                values[app_key][model.__name__]['to_many'] = [
                    self._get_model_field_info(model, x) for x in dir(model)
                    if isinstance(getattr(model, x), ManyToManyDescriptor)
                ]

        return values

    @cache
    def _get_models_dependencies(self) -> list[Model]:
        values = {}
        descriptors = self._get_models_descriptors()
        for app_key in descriptors:
            for descriptor_key in descriptors[app_key]:
                descriptor = descriptors[app_key][descriptor_key]

                if app_key not in values:
                    values[app_key] = set()

                primary_values = values[app_key]['primary'] if 'primary' in values[app_key] else []
                secondary_values = values[app_key]['secondary'] if 'secondary' in values[app_key] else []

                values[app_key] = {
                    'primary': {
                        *primary_values, *[
                            x['app_name']
                            for x in descriptor['to_one'] if x['app_name'] != app_key and x['null'] == False
                        ], *[
                            x['app_name']
                            for x in descriptor['to_many'] if x['app_name'] != app_key and x['null'] == False
                        ]
                    },
                    'secondary': {
                        *secondary_values, *[
                            x['app_name']
                            for x in descriptor['to_one'] if x['app_name'] != app_key and x['null'] == True
                        ], *[
                            x['app_name']
                            for x in descriptor['to_many'] if x['app_name'] != app_key and x['null'] == True
                        ]
                    },
                }

        return values

    def _sort_models_handlers(self,
                              dependencies_resolved=None,
                              primary_values=None,
                              secondary_values=None,
                              primary_dependencies=None,
                              secondary_dependencies=None,
                              consume_primary=True) -> list[Model]:

        dependencies_resolved = dependencies_resolved or set()
        primary_values = primary_values or []
        secondary_values = secondary_values or []

        if not primary_dependencies and not secondary_dependencies:
            dependencies = self._get_models_dependencies()

            primary_dependencies = {}
            for x in dependencies:
                primary_dependencies[x] = dependencies[x]['primary']

            secondary_dependencies = {}
            for x in dependencies:
                secondary_dependencies[x] = dependencies[x]['secondary']

        for dependency in dependencies_resolved:
            for key in primary_dependencies:

                if dependency in primary_dependencies[key]:
                    primary_dependencies[key].remove(dependency)

        primary_found = [
            x for x in [y for y in primary_dependencies if y not in dependencies_resolved]
            if len(primary_dependencies[x]) == 0
        ]

        for x in primary_found:
            dependencies_resolved.add(x)

        secondary_found = [
            x for x in [y for y in secondary_dependencies if y not in dependencies_resolved]
            if len(secondary_dependencies[x]) == 0
        ]

        if consume_primary and primary_found:
            primary_values.append(primary_found)

        elif not consume_primary and secondary_found:
            secondary_values.append(secondary_found)

        for x in primary_found:
            del primary_dependencies[x]

            for dependency in primary_dependencies:
                if x in primary_dependencies[dependency]:
                    primary_dependencies[dependency].remove(x)

        if primary_dependencies:
            return self._sort_models_handlers(dependencies_resolved,
                                              primary_values,
                                              secondary_values,
                                              primary_dependencies,
                                              secondary_dependencies,
                                              consume_primary=True)

        if secondary_dependencies:
            return primary_values, [x for x in secondary_dependencies if len(secondary_dependencies[x])]

        return primary_values, secondary_values

    @cache
    def _get_models_handlers(self) -> list[Model]:
        arguments = {}
        arguments_banned = set()
        order, deferred = self._sort_models_handlers()
        descriptors = self._get_models_descriptors()

        def manage_model(models, descriptor, *args, **kwargs):
            model_field_name = self.camel_case_to_snake_case(descriptor['meta']['model_name'])
            app_name = descriptor['meta']['app_name']
            model_name = descriptor['meta']['model_name']

            if model_field_name in kwargs and f'{app_name}__{model_field_name}' in kwargs:
                raise Exception(f'Exists many apps with the same model name `{model_name}`, please use '
                                f'`{app_name}__{model_field_name}` instead of `{model_field_name}`')

            arg = False
            if f'{app_name}__{model_field_name}' in kwargs:
                arg = kwargs[f'{app_name}__{model_field_name}']

            elif model_field_name in kwargs:
                arg = kwargs[model_field_name]

            if not model_field_name in models and is_valid(arg):
                kargs = {}

                for x in descriptor['to_one']:
                    related_model_field_name = self.camel_case_to_snake_case(x['model_name'])
                    if related_model_field_name in models:
                        kargs[x['field']] = just_one(models[related_model_field_name])

                without_through = [x for x in descriptor['to_many'] if x['custom_through'] == False]
                for x in without_through:
                    related_model_field_name = self.camel_case_to_snake_case(x['model_name'])

                    if related_model_field_name in models:
                        kargs[x['field']] = get_list(models[related_model_field_name])

                models[model_field_name] = create_models(arg, f'{app_name}.{model_name}', **kargs)

                with_through = [
                    x for x in descriptor['to_many']
                    if x['custom_through'] == True and not x['field'].endswith('_set')
                ]
                for x in with_through:
                    related_model_field_name = self.camel_case_to_snake_case(x['model_name'])
                    if related_model_field_name in models:

                        for item in get_list(models[related_model_field_name]):
                            through_current = x['through_fields'][0]
                            through_related = x['through_fields'][1]
                            through_args = {through_current: models[model_field_name], through_related: item}

                            x['handler'].through.objects.create(**through_args)

            return models

        def link_deferred_model(models, descriptor, *args, **kwargs):
            model_field_name = self.camel_case_to_snake_case(descriptor['meta']['model_name'])
            app_name = descriptor['meta']['app_name']
            model_name = descriptor['meta']['model_name']

            if model_field_name in kwargs and f'{app_name}__{model_field_name}' in kwargs:
                raise Exception(f'Exists many apps with the same model name `{model_name}`, please use '
                                f'`{app_name}__{model_field_name}` instead of `{model_field_name}`')

            if model_field_name in models:
                items = models[model_field_name] if isinstance(models[model_field_name],
                                                               list) else [models[model_field_name]]
                for m in items:

                    for x in descriptor['to_one']:
                        related_model_field_name = self.camel_case_to_snake_case(x['model_name'])
                        model_exists = related_model_field_name in models
                        is_list = isinstance(models[model_field_name], list) if model_exists else False
                        if model_exists and not is_list and not getattr(models[model_field_name], x['field']):
                            setattr(m, x['field'], just_one(models[related_model_field_name]))

                        if model_exists and is_list:
                            for y in models[model_field_name]:
                                if getattr(y, x['field']):
                                    setattr(m, x['field'], just_one(models[related_model_field_name]))

                    for x in descriptor['to_many']:
                        related_model_field_name = self.camel_case_to_snake_case(x['model_name'])
                        if related_model_field_name in models and not getattr(
                                models[model_field_name], x['field']):
                            setattr(m, x['field'], get_list(models[related_model_field_name]))

                    setattr(m, '__mixer__', None)
                    m.save()

            return models

        def wrapper(*args, **kwargs):
            models = {}
            for generation_round in order:
                for app_key in generation_round:
                    for descriptor_key in descriptors[app_key]:
                        descriptor = descriptors[app_key][descriptor_key]
                        attr = self.camel_case_to_snake_case(descriptor['meta']['model_name'])

                        models = manage_model(models, descriptor, *args, **kwargs)

                        if app_key not in arguments:
                            arguments[app_key] = {}
                            arguments[attr] = ...

                        else:
                            arguments_banned.add(attr)

                        arguments[f'{app_key}__{attr}'] = ...

            for generation_round in order:
                for app_key in generation_round:
                    for descriptor_key in descriptors[app_key]:
                        descriptor = descriptors[app_key][descriptor_key]
                        attr = self.camel_case_to_snake_case(descriptor['meta']['model_name'])

                        models = link_deferred_model(models, descriptor, *args, **kwargs)

                        if app_key not in arguments:
                            arguments[app_key] = {}
                            arguments[attr] = ...

                        else:
                            arguments_banned.add(attr)

                        arguments[f'{app_key}__{attr}'] = ...

            return AttrDict(**models)

        return wrapper

    def create_v2(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        Unstable version of mixin that create all models, do not use this.
        """
        models = self._get_models_handlers()(*args, **kwargs)
        return models

    def create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        Create one o many instances of models and return it like a dict of models.

        Usage:

        ```py
        # create three users
        self.bc.database.create(user=3)

        # create one user with a specific first name
        user = {'first_name': 'Lacey'}
        self.bc.database.create(user=user)

        # create two users with a specific first name and last name
        users = [
            {'first_name': 'Lacey', 'last_name': 'Sturm'},
            {'first_name': 'The', 'last_name': 'Warning'},
        ]
        self.bc.database.create(user=users)

        # create two users with the same first name
        user = {'first_name': 'Lacey'}
        self.bc.database.create(user=(2, user))

        # setting up manually the relationships
        cohort_user = {'cohort_id': 2}
        self.bc.database.create(cohort=2, cohort_user=cohort_user)
        ```

        It get the model name as snake case, you can pass a `bool`, `int`, `dict`, `tuple`, `list[dict]` or
        `list[tuple]`.

        Behavior for type of argument:

        - `bool`: if it is true generate a instance of a model.
        - `int`: generate a instance of a model n times, if `n` > 1 this is a list.
        - `dict`: generate a instance of a model, this pass to mixer.blend custom values to the model.
        - `tuple`: one element need to be a int and the other be a dict, generate a instance of a model n times,
        if `n` > 1 this is a list, this pass to mixer.blend custom values to the model.
        - `list[dict]`: generate a instance of a model n times, if `n` > 1 this is a list,
        this pass to mixer.blend custom values to the model.
        - `list[tuple]`: generate a instance of a model n times, if `n` > 1 this is a list for each element,
        this pass to mixer.blend custom values to the model.

        Keywords arguments deprecated:
        - models: this arguments is use to implement inheritance, receive as argument the output of other
        `self.bc.database.create()` execution.
        - authenticate: create a user and use `APITestCase.client.force_authenticate(user=models['user'])` to
        get credentials.
        """

        return GenerateModelsMixin.generate_models(self._parent, _new_implementation=True, *args, **kwargs)

    @database_sync_to_async
    def async_create(self, *args, **kwargs) -> dict[str, Model | list[Model]]:
        """
        This is a wrapper for `Model.objects.count()`, get how many instances of this `Model` are saved.

        Keywords arguments:
        - path(`str`): path to a model, for example `admissions.CohortUser`.
        """

        return self.create(*args, **kwargs)
