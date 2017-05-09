"""common code for all experiments
"""
from __future__ import print_function

from tensorflow.python.client import device_lib
print(device_lib.list_local_devices())

import numpy as np
np.random.seed(1337)
import keras
import medleydb as mdb
import os

import core
import evaluate

SAMPLES_PER_EPOCH = 256
NB_EPOCHS = 50
NB_VAL_SAMPLES = 512


def train(model, model_save_path, dat_type):

    if dat_type == 'multif0_complete':
        data_path = core.data_path_multif0_complete()
    elif dat_type == 'multif0_incomplete':
        data_path = core.data_path_multif0_incomplete()
    elif dat_type == 'melody3':
        data_path = core.data_path_melody3()
    elif dat_type == 'melody2':
        data_path = core.data_path_melody2()
    elif dat_type == 'melody1':
        data_path = core.data_path_melody1()
    elif dat_type == 'pitch':
        data_path = core.data_path_pitch()
    elif dat_type == 'bass':
        data_path = core.data_path_bass()
    elif dat_type == 'vocal':
        data_path = core.data_path_vocal()
    else:
        raise ValueError("Invalid value for dat_type")

    mtrack_list = core.track_id_list()
    input_patch_size = core.patch_size()

    ### DATA SETUP ###
    dat = core.Data(
        mtrack_list, data_path, input_patch_size=input_patch_size
    )
    train_generator = dat.get_train_generator()
    validation_generator = dat.get_validation_generator()

    model.compile(
        loss=core.bkld, metrics=['mse', core.soft_binary_accuracy],
        optimizer='adam'
    )

    print(model.summary(line_length=80))

    ### FIT MODEL ###
    history = model.fit_generator(
        train_generator, SAMPLES_PER_EPOCH, epochs=NB_EPOCHS, verbose=1,
        validation_data=validation_generator, validation_steps=NB_VAL_SAMPLES,
        callbacks=[
            keras.callbacks.ModelCheckpoint(
                model_save_path, save_best_only=True, verbose=1),
            keras.callbacks.ReduceLROnPlateau(patience=5, verbose=1),
            keras.callbacks.EarlyStopping(patience=6, verbose=0)
        ]
    )

    ### load best weights ###
    model.load_weights(model_save_path)

    return model, history, dat


def run_evaluation_multif0(exper_dir, save_key, history, dat, model):

    (save_path, _, plot_save_path,
     model_scores_path, _, _
    ) = evaluate.get_paths(exper_dir, save_key)

    ### Results plots ###
    print("plotting results...")
    evaluate.plot_metrics_epochs(history, plot_save_path)

    ### Evaluate ###
    print("getting model metrics...")
    evaluate.get_model_metrics(dat, model, model_scores_path)

    print("getting best threshold...")
    thresh = evaluate.get_best_thresh_multif0(dat, model)
    with open(os.path.join(save_path, "best_thresh.json", 'w')) as fhandle:
        json.dump({'best_thresh': thresh}, fhandle)

    print("scoring multif0 metrics on test sets...")
    print("    > bach10...")
    evaluate.score_multif0_on_test_set('bach10', model, save_path, thresh)
    print("    > medleydb test...")
    evaluate.score_multif0_on_test_set('mdb_test', model, save_path, thresh)
    print("    > su...")
    evaluate.score_multif0_on_test_set('su', model, save_path, thresh)


def run_evaluation_singlef0(exper_dir, save_key, history, dat, model):
    (save_path, _, plot_save_path,
     model_scores_path, _, _
    ) = evaluate.get_paths(exper_dir, save_key)

    ### Results plots ###
    print("plotting results...")
    evaluate.plot_metrics_epochs(history, plot_save_path)

    ### Evaluate ###
    print("getting model metrics...")
    evaluate.get_model_metrics(dat, model, model_scores_path)

    print("getting best threshold...")
    thresh = evaluate.get_best_thresh_singlef0(dat, model)
    with open(os.path.join(save_path, "best_thresh.json", 'w')) as fhandle:
        json.dump({'best_thresh': thresh}, fhandle)

    print("scoring multif0 metrics on test set...")
    evaluate.score_singlef0_on_test_set(model, dat, save_path, thresh)


def experiment(save_key, model, dat_type, eval_type=None):
    """common code for all experiments
    """
    exper_dir = core.experiment_output_path()

    (save_path, model_save_path, _, _, _, _) = evaluate.get_paths(
        exper_dir, save_key
    )

    model, history, dat = train(model, model_save_path, dat_type)

    if eval_type == None:
        if dat_type in ['multif0_complete', 'multif0_incomplete', 'melody3']:
            eval_type = 'multif0'
        else:
            eval_type = 'singlef0'

    if eval_type == 'multif0':
        run_evaluation_multif0(exper_dir, save_key, history, dat, model)
    elif eval_type == 'singlef0':
        run_evaluation_singlef0(exper_dir, save_key, history, dat, model)

    print("done!")
    print("Results saved to {}".format(save_path))

