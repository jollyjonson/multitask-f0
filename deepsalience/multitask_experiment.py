from __future__ import print_function

import argparse

import multitask_core as MC
import multitask_evaluate as ME
import keras
import os
import json


def main(model, output_path, loss_weights, sample_weight_mode,
         task_indices, data_types=None, tasks=None, mux_weights=None,
         samples_per_epoch=50, nb_epochs=200, nb_val_samples=10,
         freq_feature=False, n_harms=5):

    data_splits = MC.load_data_splits()

    if data_types is None:
        data_types = MC.DATA_TYPES
    else:
        data_types = data_types

    if tasks is None:
        tasks = MC.TASKS
    else:
        tasks = tasks

    if mux_weights is None:
        mux_weights = None
    else:
        mux_weights = mux_weights

    if not os.path.exists(output_path):
        os.mkdir(output_path)

    model_save_path = os.path.join(output_path, "model_weights.h5")
    history_plot_path = os.path.join(output_path, "training_history.pdf")

    augment = True

    train_generator = MC.multitask_generator(
        data_splits['train'], data_types=data_types,
        tasks=tasks, mux_weights=mux_weights,
        add_frequency=freq_feature, augment=augment,
        n_harms=n_harms)
    validate_generator = MC.multitask_generator(
        data_splits['validate'], data_types=data_types,
        tasks=tasks, mux_weights=mux_weights,
        add_frequency=freq_feature, augment=augment,
        n_harms=n_harms)
    test_generator = MC.multitask_generator(
        data_splits['test'], data_types=data_types,
        tasks=tasks, mux_weights=mux_weights,
        add_frequency=freq_feature, augment=augment,
        n_harms=n_harms)

    model.compile(
        loss=MC.bkld, metrics=['mse', MC.soft_binary_accuracy],
        loss_weights=loss_weights,
        optimizer='adam', sample_weight_mode=sample_weight_mode
    )

    if not os.path.exists(model_save_path):
        history = model.fit_generator(
            train_generator, samples_per_epoch, epochs=nb_epochs, verbose=1,
            validation_data=validate_generator, validation_steps=nb_val_samples,
            callbacks=[
                keras.callbacks.ModelCheckpoint(
                    model_save_path, save_best_only=True, verbose=1),
                keras.callbacks.ReduceLROnPlateau(patience=5, verbose=1),
                keras.callbacks.EarlyStopping(patience=25, verbose=0)
            ]
        )

        MC.history_plot(history, tasks, history_plot_path)

    model.load_weights(model_save_path)

    threshold_path = os.path.join(
        output_path, 'evaluation', 'thresholds.json')
    if os.path.exists(threshold_path):
	with open(threshold_path, 'r') as fhandle:
        	thresholds = json.load(fhandle)
    else:
        thresholds = None

    thresholds, scores = ME.evaluate_model(
        model, tasks, task_indices, add_frequency=freq_feature,
        n_harms=n_harms, thresholds=thresholds)
    ME.save_eval(output_path, thresholds, scores)

