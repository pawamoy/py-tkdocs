"""Tests for [the `loader` module][pytkdocs.loader]."""

import os
import sys
from pathlib import Path
from typing import Set

import pytest
from django.db.models.fields import CharField
from marshmallow import fields

from pytkdocs.loader import Loader, get_object_tree
from tests import FIXTURES_DIR


def test_import_no_path():
    """Raise error when getting tree for empty object name."""
    with pytest.raises(ValueError):
        get_object_tree("")


def test_import_error():
    """Raise error when getting tree for missing object."""
    with pytest.raises(ImportError):
        get_object_tree("eeeeeeeeeeeeeeeeeee")


def test_can_find_class_real_path():
    """Find real path of a class."""
    leaf = get_object_tree("tests.fixtures.real_path.module_a.DefinedInModuleB")
    assert leaf.dotted_path == "tests.fixtures.real_path.module_b.DefinedInModuleB"


def test_can_find_class_method_real_path():
    """Find real path of a class method."""
    leaf = get_object_tree("tests.fixtures.real_path.module_a.DefinedInModuleB.method")
    assert leaf.dotted_path == "tests.fixtures.real_path.module_b.DefinedInModuleB.method"


def test_can_find_class_attribute_real_path():
    """Find real path of a class attribute."""
    leaf = get_object_tree("tests.fixtures.real_path.module_a.DefinedInModuleB.ATTRIBUTE")
    assert leaf.dotted_path == "tests.fixtures.real_path.module_b.DefinedInModuleB.ATTRIBUTE"


def test_cannot_find_module_attribute_real_path():
    """Find real path of a module attribute."""
    leaf = get_object_tree("tests.fixtures.real_path.module_a.ATTRIBUTE")
    assert leaf.dotted_path != "tests.fixtures.real_path.module_b.ATTRIBUTE"


def test_import_module_with_colon_path_syntax():
    """Import a module using the "colon" path syntax."""
    leaf = get_object_tree("tests.fixtures.the_package.the_module", new_path_syntax=True)


def test_import_attribute_with_colon_path_syntax():
    """Import an attribute using the "colon" path syntax."""
    leaf = get_object_tree("tests.fixtures.the_package.the_module:THE_ATTRIBUTE")


def test_import_nested_attribute_with_colon_path_syntax():
    """Import a nested attribute using the "colon" path syntax."""
    leaf = get_object_tree("tests.fixtures.the_package.the_module:TheClass.THE_ATTRIBUTE")


def test_fail_to_import_module_with_colon_path_syntax():
    """Import a module using the "colon" path syntax."""
    with pytest.raises(ImportError):
        get_object_tree("tests.fixtures.does_not_exist", new_path_syntax=True)


def test_fail_to_import_attribute_with_colon_path_syntax():
    """Import an attribute using the "colon" path syntax."""
    with pytest.raises(AttributeError) as error:
        leaf = get_object_tree("tests.fixtures.the_package.the_module:does_not_exist")


def test_fail_to_import_nested_attribute_with_colon_path_syntax():
    """Import a nested attribute using the "colon" path syntax."""
    with pytest.raises(AttributeError) as error:
        leaf = get_object_tree("tests.fixtures.the_package.the_module:TheClass.does_not_exist")


def test_fail_to_import_module_with_dot_path_syntax():
    """Import a module using the "dot" path syntax."""
    with pytest.raises(ImportError, match=r"possible causes"):
        get_object_tree("does_not_exist")


def test_fail_to_import_attribute_with_dot_path_syntax():
    """Import an attribute using the "dot" path syntax."""
    with pytest.raises(AttributeError) as error:
        leaf = get_object_tree("tests.fixtures.the_package.the_module.does_not_exist")


def test_fail_to_import_nested_attribute_with_dot_path_syntax():
    """Import a nested attribute using the "dot" path syntax."""
    with pytest.raises(AttributeError) as error:
        leaf = get_object_tree("tests.fixtures.the_package.the_module.TheClass.does_not_exist")


def test_inheriting_enum_Enum():
    """Handle `enum.Enum` classes."""
    """See  details at [tests.fixtures.inheriting_enum_Enum][]."""
    loader = Loader()
    loader.get_object_documentation("tests.fixtures.inheriting_enum_Enum")
    assert not loader.errors


def test_inheriting_typing_NamedTuple():
    """
    Handle `typing.NamedTuple classes`.

    See details at [tests.fixtures.inheriting_typing_NamedTuple][].
    """
    loader = Loader()
    loader.get_object_documentation("tests.fixtures.inheriting_typing_NamedTuple")

    if sys.version_info > (3, 7, 99):
        assert len(loader.errors) == 1
    else:
        # there are 4 class-attributes, 2 errors (source, signature) per attribute
        assert len(loader.errors) >= 8
        for error in loader.errors[-8:]:
            assert "itemgetter" in error
        for error in loader.errors[:-8]:
            assert "could not get source code" in error


def test_nested_class():
    """Handle nested classes."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.nested_class")
    assert obj.classes
    assert obj.classes[0].docstring == "Main docstring."
    assert obj.classes[0].classes
    assert obj.classes[0].classes[0].docstring == "Nested docstring."


def test_loading_deep_package():
    """Handle deep nesting of packages."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.pkg1.pkg2.pkg3.pkg4.pkg5")
    assert obj.docstring == "Hello from the abyss."
    assert obj.path == "tests.fixtures.pkg1.pkg2.pkg3.pkg4.pkg5"


def test_loading_package():
    """Handle basic packages."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package")
    assert obj.docstring == "The package docstring."


def test_loading_namespace_package():
    """Handle native namespace packages."""
    loader = Loader()
    old_paths = list(sys.path)
    sys.path.append(str(Path(FIXTURES_DIR).resolve()))
    obj = loader.get_object_documentation("test_namespace.subspace")
    assert obj.docstring == "The subspace package docstring."
    assert obj.relative_file_path == f"subspace{os.sep}__init__.py"
    sys.path = old_paths


def test_loading_module():
    """Handle single modules."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module")
    assert obj.docstring == "The module docstring."


def test_loading_class():
    """Handle classes."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass")
    assert obj.docstring == "The class docstring."
    assert obj.bases == ["object"]


def test_loading_class_with_multiline_docstring_starting_on_first_line():
    """Handle classes with multiline docstrings where the first line is next to the triple-quotes."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.first_line_class_docstring.TheClass")
    assert obj.docstring == """The first line of the docstring.\n\nA bit more of the docstring."""


def test_loading_dataclass():
    """Handle dataclasses."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.dataclass.Person")
    assert obj.docstring == "Simple dataclass for a person's information"
    assert len(obj.attributes) == 2
    name_attr = next(attr for attr in obj.attributes if attr.name == "name")
    assert name_attr.type == str
    age_attr = next(attr for attr in obj.attributes if attr.name == "age")
    assert age_attr.type == int
    assert age_attr.docstring == "Field description."
    assert "dataclass" in obj.properties

    not_dataclass = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.TheNestedClass")
    assert "dataclass" not in not_dataclass.properties


def test_loading_empty_dataclass():
    """Handle empty dataclasses."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.dataclass.Empty")
    assert obj.docstring == "A dataclass without any fields"
    assert len(obj.attributes) == 0
    assert "dataclass" in obj.properties


def test_loading_pydantic_model():
    """Handle Pydantic models."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.pydantic.Person")
    assert obj.docstring == "Simple Pydantic Model for a person's information"
    assert "pydantic-model" in obj.properties
    name_attr = next(attr for attr in obj.attributes if attr.name == "name")
    assert name_attr.type == str
    assert name_attr.docstring == "The person's name"
    assert "pydantic-field" in name_attr.properties
    age_attr = next(attr for attr in obj.attributes if attr.name == "age")
    assert age_attr.type == int
    assert age_attr.docstring == "The person's age which must be at minimum 18"
    assert "pydantic-field" in age_attr.properties
    labels_attr = next(attr for attr in obj.attributes if attr.name == "labels")
    assert labels_attr.type == Set[str]
    assert labels_attr.docstring == "Set of labels the person can be referred by"
    assert "pydantic-field" in labels_attr.properties


def test_loading_django_model():
    """Handle Django models"""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.django.Person")
    assert obj.docstring == "Simple Django Model for a person's information"
    name_attr = next(attr for attr in obj.attributes if attr.name == "name")
    assert name_attr.type == CharField
    assert name_attr.docstring == "Name"


def test_loading_marshmallow_model():
    """Handle Marshmallow models."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.marshmallow.Person")
    assert obj.docstring == "Simple Marshmallow Model for a person's information"
    assert "marshmallow-model" in obj.properties
    name_attr = next(attr for attr in obj.attributes if attr.name == "name")
    assert name_attr.type == fields.Str
    assert name_attr.docstring == "The person's name"
    assert "marshmallow-field" in name_attr.properties
    assert "required" in name_attr.properties
    age_attr = next(attr for attr in obj.attributes if attr.name == "age")
    assert age_attr.type == fields.Int
    assert age_attr.docstring == "The person's age which must be at minimum 18"
    assert "marshmallow-field" in age_attr.properties


def test_loading_nested_class():
    """Select nested class."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.TheNestedClass")
    assert obj.docstring == "The nested class docstring."


def test_loading_double_nested_class():
    """Select double-nested class."""
    loader = Loader()
    obj = loader.get_object_documentation(
        "tests.fixtures.the_package.the_module.TheClass.TheNestedClass.TheDoubleNestedClass"
    )
    assert obj.docstring == "The double nested class docstring."


def test_loading_class_attribute():
    """Select class attribute."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.THE_ATTRIBUTE")
    assert obj.docstring == "The attribute 0.1 docstring."


def test_loading_nested_class_attribute():
    """Select nested-class attribute."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.TheNestedClass.THE_ATTRIBUTE")
    assert obj.docstring == "The attribute 0.2 docstring."


def test_loading_double_nested_class_attribute():
    """Select double-nested-class attribute."""
    loader = Loader()
    obj = loader.get_object_documentation(
        "tests.fixtures.the_package.the_module.TheClass.TheNestedClass.TheDoubleNestedClass.THE_ATTRIBUTE"
    )
    assert obj.docstring == "The attribute 0.3 docstring."


def test_loading_class_method():
    """Select class method."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_method")
    assert obj.docstring == "The method1 docstring."


def test_loading_nested_class_method():
    """Select nested class method."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.TheNestedClass.the_method")
    assert obj.docstring == "The method2 docstring."


def test_loading_double_nested_class_method():
    """Select double-nested class method."""
    loader = Loader()
    obj = loader.get_object_documentation(
        "tests.fixtures.the_package.the_module.TheClass.TheNestedClass.TheDoubleNestedClass.the_method"
    )
    assert obj.docstring == "The method3 docstring."


def test_loading_staticmethod():
    """Select static method."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_static_method")
    assert obj.docstring == "The static method docstring."


def test_loading_classmethod():
    """Select class method."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_class_method")
    assert obj.docstring == "The class method docstring."


def test_loading_property():
    """Select property."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_property")
    assert obj.docstring == "The property docstring."


def test_loading_writable_property():
    """Select writable property."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_writable_property")
    assert obj.docstring == "The writable property getter docstring."


def test_loading_function():
    """Select function."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.the_function")
    assert obj.docstring == "The function docstring."


def test_loading_attribute():
    """Select attribute."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.THE_ATTRIBUTE")
    assert obj.docstring == "The attribute docstring."


def test_loading_explicit_members():
    """Select members explicitly."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module", members={"TheClass"})
    assert len(obj.children) == 1
    assert obj.children[0].name == "TheClass"


def test_loading_no_members():
    """Select no members."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module", members=False)
    assert not obj.children


def test_loading_with_filters():
    """Select with filters."""
    loader = Loader(filters=["!^[A-Z_]+$"])
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module")
    for child in obj.children:
        assert child.name != "THE_ATTRIBUTE"


def test_loading_with_filters_reselection():
    """A filter can cancel a previous filter."""
    loader = Loader(filters=["![A-Z_]", "[a-z]"])
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module")
    assert obj.classes
    assert obj.classes[0].name == "TheClass"


def test_loading_with_members_and_filters():
    """Select members with filters."""
    loader = Loader(filters=["!THE"])
    obj = loader.get_object_documentation(
        "tests.fixtures.the_package.the_module", members={"THE_ATTRIBUTE", "TheClass"}
    )
    assert obj.attributes
    assert obj.attributes[0].name == "THE_ATTRIBUTE"
    assert obj.classes
    assert obj.classes[0].name == "TheClass"
    assert not any(a.name == "THE_ATTRIBUTE" for a in obj.classes[0].attributes)


def test_loading_members_set_at_import_time():
    """Select dynamic members."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.dynamic_members")
    assert obj.functions
    assert len(obj.classes) == 1
    class_ = obj.classes[0]
    assert class_.methods


def test_loading_inherited_members():
    """Select inherited members."""
    loader = Loader(inherited_members=True)
    obj = loader.get_object_documentation("tests.fixtures.inherited_members.Child")
    for child_name in ("method1", "method2", "V1", "V2"):
        assert child_name in (child.name for child in obj.children)


def test_not_loading_inherited_members():
    """Do not select inherited members."""
    loader = Loader(inherited_members=False)
    obj = loader.get_object_documentation("tests.fixtures.inherited_members.Child")
    for child_name in ("method1", "V1"):
        assert child_name not in (child.name for child in obj.children)
    for child_name in ("method2", "V2"):
        assert child_name in (child.name for child in obj.children)


def test_loading_selected_inherited_members():
    """Select specific members, some of them being inherited."""
    loader = Loader(inherited_members=True)
    obj = loader.get_object_documentation("tests.fixtures.inherited_members.Child", members={"V1", "V2"})
    for child_name in ("V1", "V2"):
        assert child_name in (child.name for child in obj.children)


def test_loading_pydantic_inherited_members():
    """Select inherited members in Pydantic models."""
    loader = Loader(inherited_members=True)
    obj = loader.get_object_documentation("tests.fixtures.inherited_members.ChildModel")
    for child_name in ("a", "b"):
        assert child_name in (child.name for child in obj.children)


def test_not_loading_pydantic_inherited_members():
    """Do not select inherited members in Pydantic models."""
    loader = Loader(inherited_members=False)
    obj = loader.get_object_documentation("tests.fixtures.inherited_members.ChildModel")
    assert "a" not in (child.name for child in obj.children)


def test_loading_wrapped_function():
    """Load documentation for wrapped function, not wrapper."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.wrapped_objects.my_function")
    assert obj.docstring == "My docstring."


def test_loading_module_wrapped_members():
    """Load documentation for wrapped function, not wrapper."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.wrapped_objects")
    assert obj.functions and obj.functions[0].docstring == "My docstring."
    assert obj.classes and obj.classes[0].methods and obj.classes[0].methods[0].docstring == "Hello!"


def test_unwrap_object_with_getattr_method_raising_exception():
    """Try loading an object that defines a `__getattr__` method which raises an exception."""
    loader = Loader()
    loader.get_object_documentation("tests.fixtures.unwrap_getattr_raises")


def test_loading_coroutine():
    """Load documentation for a coroutine."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.asyncio.coroutine_function")
    assert "async" in obj.properties


def test_loading_coroutine_method():
    """Load documentation for a coroutine method."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.asyncio.ClassContainingCoroutineMethod.coroutine_method")
    assert "async" in obj.properties


def test_loading_function_without_async_property():
    """Load documentation for a function that is not a coroutine."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.the_function")
    assert "async" not in obj.properties


def test_loading_method_without_async_property():
    """Load documentation for a method that is not a coroutine."""
    loader = Loader()
    obj = loader.get_object_documentation("tests.fixtures.the_package.the_module.TheClass.the_method")
    assert "async" not in obj.properties


def test_inherited_properties_docstrings():
    """Load docstrings from parent class for inherited properties."""
    loader = Loader(new_path_syntax=True)
    obj = loader.get_object_documentation("tests.fixtures.inherited_properties:SubClass.read_only")
    assert obj.docstring == "SuperClass.read_only docs"
    obj = loader.get_object_documentation("tests.fixtures.inherited_properties:SubClass.mutable")
    assert obj.docstring == "SuperClass.mutable getter docs"


def test_loading_cached_properties():
    """Load cached properties."""
    loader = Loader(new_path_syntax=True)
    obj = loader.get_object_documentation("tests.fixtures.cached_properties:C")
    assert len(obj.children) == 1
    assert obj.children[0].name == obj.children[0].docstring == "aaa"
    assert "cached" in obj.children[0].properties


def test_method_descriptor():
    """Load a method descriptor."""
    loader = Loader(new_path_syntax=True)
    obj = loader.get_object_documentation("tests.fixtures.method_descriptor:descriptor")
    assert obj.name == "descriptor"
    assert obj.signature
    assert len(obj.signature.parameters) == 2
    assert obj.docstring
    assert obj.category == "method"


def test_load_decorated_function():
    """Load a decorated function."""
    loader = Loader(new_path_syntax=True)
    obj = loader.get_object_documentation("tests.fixtures.decorated_function")
    assert [child.name for child in obj.children] == ["add", "sub"]
    for child in obj.children:
        assert child.category == "function"
        assert child.parent is child.root
        assert child.parent.name == "decorated_function"

def test_load_final_annotations():
    """Load things annotated as final."""
    loader = Loader(new_path_syntax=True)
    obj = loader.get_object_documentation("tests.fixtures.final")
