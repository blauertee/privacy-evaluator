from typing import Dict
import numpy as np

from privacy_evaluator.metrics.basics import (
    accuracy,
    train_to_test_accuracy_gap,
    train_to_test_accuracy_ratio,
)
from privacy_evaluator.attacks.attack import Attack
from privacy_evaluator.classifiers.classifier import Classifier


class MembershipInferenceAttack(Attack):
    """MembershipInferenceAttack base class."""

    _ART_MEMBERSHIP_INFERENCE_ATTACK_MODULE = (
        "art.attacks.inference.membership_inference"
    )

    def __init__(
        self,
        target_model: Classifier,
        x_train: np.ndarray,
        y_train: np.ndarray,
        x_test: np.ndarray,
        y_test: np.ndarray,
        **kwargs
    ):
        """Initializes a MembershipInferenceAttack class.

        :param target_model: Target model to be attacked.
        :param x_train: Data that was used to train the target model.
        :param y_train: Labels for the data that was used to train the target model.
        :param x_test: Data that was not used to train the target model.
        :param y_test: Labels for the data that was not used to train the target model.
        """
        super().__init__(target_model, x_train, y_train, x_test, y_test)
        self._art_attack = self._init_art_attack(target_model, **kwargs)
        self._art_attack_model_fitted = False

    def attack(self, x: np.ndarray, y: np.ndarray, **kwargs) -> np.ndarray:
        """Performs the membership inference attack on the target model.

        :param x: Input data to attack.
        :param y: True labels for `x`.
        :param kwargs: Keyword arguments of the attack.
        :return: An array holding the inferred membership status, 1 indicates a member and 0 indicates non-member.
        :raises Exception: If attack model is not fitted.
        """
        if self._art_attack_model_fitted is False:
            raise Exception(
                "The attack model needs to be fitted first. Please run `fit()` on the attack."
            )
        return self._art_attack.infer(x, y)

    def attack_output(self, x: np.ndarray, y: np.ndarray, y_attack: np.ndarray) -> Dict:
        """Creates attack output metrics in an extractable format.

        :param x: Input data to attack.
        :param y: True labels for `x`.
        :param y_attack: True labels for the attack model (e.g. the membership status).
        :return: An dict with attack output metrics including the target model train and test accuracy, target model
        train to test accuracy gap and ratio and the attack model accuracy.
        """

        train_accuracy = accuracy(self.y_train, self.target_model.predict(self.x_train))
        test_accuracy = accuracy(self.y_test, self.target_model.predict(self.x_test))
        y_attack_prediction = self.attack(x, y)

        return {
            "target_model_train_accuracy": train_accuracy,
            "target_model_test_accuracy": test_accuracy,
            "target_model_train_to_test_accuracy_gap": train_to_test_accuracy_gap(
                train_accuracy, test_accuracy
            ),
            "target_model_train_to_test_accuracy_ratio": train_to_test_accuracy_ratio(
                train_accuracy, test_accuracy
            ),
            "attack_model_accuracy": accuracy(y_attack, y_attack_prediction),
        }

    def fit(self, **kwargs):
        """Fits the attack model.

        :param kwargs: Keyword arguments for the fitting.
        """
        raise NotImplementedError(
            "Method `attack()` needs to be implemented in subclass"
        )

    @classmethod
    def _art_module(cls) -> str:
        """Returns the matching ART module for this class.

        :return: Matching ART module.
        """
        return cls._ART_MEMBERSHIP_INFERENCE_ATTACK_MODULE

    @classmethod
    def _art_class(cls) -> str:
        """Returns the matching ART class for this class.

        :return: Matching ART class.
        :raises AttributeError: If `_ART_MEMBERSHIP_INFERENCE_ATTACK_CLASS` is not defined.

        """
        try:
            return cls._ART_MEMBERSHIP_INFERENCE_ATTACK_CLASS
        except AttributeError:
            raise AttributeError(
                "Attribute `_ART_MEMBERSHIP_INFERENCE_ATTACK_CLASS` needs to be defined in subclass."
            )

    @classmethod
    def _init_art_attack(cls, target_model: Classifier, **kwargs):
        """Initializes an ART attack.

        :param target_model: Target model to be attacked.
        :param kwargs: Keyword arguments of the attack.
        :return: Instance of an ART attack.
        """
        _art_module = __import__(cls._art_module(), fromlist=[cls._art_class()])
        _art_class = getattr(_art_module, cls._art_class())
        return _art_class(target_model.to_art_classifier(), **kwargs)

    @staticmethod
    def _fit_decorator(fit_function):
        """Decorator for the `fit()` methods of the subclasses.

        Defines a decorator method which checks weather attack model was already fitted. If not, attack model is fitted and
        `_art_attack_model_fitted` is set to `True`.

        :return: Decorator method.
        """

        def __fit_decorator(self, **kwargs):
            if self._art_attack_model_fitted is False:
                fit_function(self, **kwargs)
                self._art_attack_model_fitted = True

        return __fit_decorator
