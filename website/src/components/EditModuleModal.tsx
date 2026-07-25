import { useEffect } from 'react';
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useUpdateModule } from '../data/designs/hooks';
import type { Module, ModulePatch } from '../data/designs/types';

const MODULE_TYPE_OPTIONS = [
  'Wall Panel',
  'Bathroom Service Wall',
  'Hospital Headwall',
  'Utility Panel',
];
const UNIT_SCALE_OPTIONS = ['METRE', 'MILLIMETRE', 'CENTIMETRE', 'FOOT', 'INCH'];

interface Props {
  module: Module;
  designId: string;
  opened: boolean;
  onClose: () => void;
}

interface FormValues {
  type: string;
  dimX: number | string;
  dimY: number | string;
  dimZ: number | string;
  roomId: string;
  unitScale: string;
}

function valuesFromModule(m: Module): FormValues {
  return {
    type: m.type ?? '',
    dimX: m.dimensions?.x ?? 0,
    dimY: m.dimensions?.y ?? 0,
    dimZ: m.dimensions?.z ?? 0,
    roomId: m.roomId ?? '',
    unitScale: m.unitScale ?? '',
  };
}

export function EditModuleModal({ module, designId, opened, onClose }: Props) {
  const update = useUpdateModule(designId);

  const form = useForm<FormValues>({
    initialValues: valuesFromModule(module),
  });

  // Re-seed the form with the latest values each time the modal opens.
  useEffect(() => {
    if (opened) form.setValues(valuesFromModule(module));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const handleClose = () => {
    if (update.isPending) return;
    onClose();
  };

  const handleSubmit = form.onSubmit((values) => {
    const patch: ModulePatch = {
      type: values.type || undefined,
      dimensions: {
        x: Number(values.dimX) || 0,
        y: Number(values.dimY) || 0,
        z: Number(values.dimZ) || 0,
      },
      roomId: values.roomId || undefined,
      unitScale: values.unitScale || undefined,
    };

    update.mutate(
      { moduleId: module.moduleId, patch },
      {
        onSuccess: () => {
          notifications.show({
            color: 'teal',
            title: 'Module updated',
            message: 'Metadata saved.',
          });
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Could not save changes.')
            : 'Could not save changes.';
          notifications.show({ color: 'red', title: 'Update failed', message });
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Edit module metadata"
      centered
      closeOnClickOutside={!update.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <Select
            label="Type"
            data={MODULE_TYPE_OPTIONS}
            searchable
            {...form.getInputProps('type')}
          />
          <Group grow>
            <NumberInput
              label="Width x (m)"
              min={0}
              step={0.1}
              decimalScale={2}
              {...form.getInputProps('dimX')}
            />
            <NumberInput
              label="Height y (m)"
              min={0}
              step={0.1}
              decimalScale={2}
              {...form.getInputProps('dimY')}
            />
            <NumberInput
              label="Depth z (m)"
              min={0}
              step={0.1}
              decimalScale={2}
              {...form.getInputProps('dimZ')}
            />
          </Group>
          <Group grow>
            <TextInput label="Room ID" {...form.getInputProps('roomId')} />
            <Select
              label="Unit scale"
              data={UNIT_SCALE_OPTIONS}
              {...form.getInputProps('unitScale')}
            />
          </Group>

          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={update.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={update.isPending}>
              Save changes
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
