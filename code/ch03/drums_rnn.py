import ast
import os
from datetime import datetime

import magenta
from bokeh.io import output_file, show
from magenta.models.drums_rnn import drums_rnn_sequence_generator
from magenta.music import midi_io
from magenta.music import notebook_utils
from magenta.music import sequence_generator_bundle
from magenta.protobuf import generator_pb2
from magenta.protobuf import music_pb2
from midi2bokeh import draw_midi

# Model name one of: [one_drum, drum_kit]
MODEL_NAME = "drum_kit"

# Bundle name is drum_kit_rnn (for both model name) TODO test this with one drum
BUNDLE_NAME = "drum_kit_rnn.mag"

# Constants
DATETIME = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
BUNDLE_DIR = "bundles"
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
  os.makedirs(OUTPUT_DIR)
MIDI_FILE = OUTPUT_DIR + "/" + MODEL_NAME + "_" + DATETIME + ".mid"
PLOT_FILE = OUTPUT_DIR + "/" + MODEL_NAME + "_" + DATETIME + ".html"

# The higher the value, the more random is the generated sequence
# 1.0 is the default value ; 1.25 is more random ; 0.75 is less random
TEMPERATURE = 1.0


# TODO repeat 4 bars then feed the output as the new primer

def get_generator():
  # Bundle TODO describe
  notebook_utils.download_bundle(BUNDLE_NAME, BUNDLE_DIR)
  bundle = sequence_generator_bundle.read_bundle_file(
    os.path.join(BUNDLE_DIR, BUNDLE_NAME))

  # Generator TODO describe
  generator_map = drums_rnn_sequence_generator.get_generator_map()
  generator = generator_map[MODEL_NAME](checkpoint=None, bundle=bundle)
  generator.initialize()

  return generator


def generate(sequence_generator, input_sequence, last_end_time, seconds_per_step, total_seconds):
  """from magenta.interfaces.midi.midi_interaction.
  CallAndResponseMidiInteraction#_generate"""

  generator_options = generator_pb2.GeneratorOptions()
  # time_start_input_section = 0
  # time_end_input_section = input_sequence.total_time
  # time_start_generate_section = time_end_input_section
  # time_end_generate_section = time_end_input_section + length
  #
  # print([str(s) for s in [time_start_input_section, time_end_input_section,
  #                         time_start_generate_section,
  #                         time_end_generate_section]])

  # last_end_time = 0.5
  # seconds_per_step = 0.125
  # total_seconds = 4.0

  # generator_options.input_sections.add(
  #   start_time=0,
  #   end_time=last_end_time)

  generator_options.generate_sections.add(
    start_time=last_end_time + seconds_per_step,
    end_time=total_seconds)

  generator_options.args['temperature'].float_value = 0.1
  generator_options.args['beam_size'].int_value = 1
  generator_options.args['branch_factor'].int_value = 1
  generator_options.args['steps_per_iteration'].int_value = 1

  sequence = sequence_generator.generate(input_sequence, generator_options)

  return sequence


if __name__ == "__main__":
  generator = get_generator()

  magenta.music.DrumTrack([frozenset([36])])
  primer_drums = magenta.music.DrumTrack(
    [frozenset(pitches) for pitches in [(41,), (41,), (41,), (), (41,)]])
  primer_sequence = primer_drums.to_sequence(qpm=120)

  qpm = 120
  # steps_per_quarter = 4
  seconds_per_step = 60.0 / qpm / generator.steps_per_quarter
  num_steps = 32
  total_seconds = num_steps * seconds_per_step

  if primer_sequence.notes:
    last_end_time = max(n.end_time for n in primer_sequence.notes)
  else:
    last_end_time = 0

  # sequence = music_pb2.NoteSequence()
  sequence = generate(generator, primer_sequence, last_end_time, seconds_per_step, total_seconds)

  plot_file = os.path.join("output", "out.html")
  midi_file = os.path.join("output", "out.mid")

  # midi
  midi_io.note_sequence_to_midi_file(sequence, midi_file)
  print(midi_file)

  # plot
  pm = midi_io.note_sequence_to_pretty_midi(sequence)
  output_file(plot_file)
  plot = draw_midi(pm)
  show(plot)
  print(plot_file)
